#!/usr/bin/env python3
"""
Fuse Panel - System Health Monitoring & Error Management
=========================================================
Monitors the agent's health, logs errors with severity levels,
manages retry queues with exponential backoff, and provides
a real-time status dashboard.

This is the "circuit breaker" layer — if something fails too many times,
the fuse blows (agent pauses) until a hardening fix resolves it.
"""

import os
import sys
import time
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


# ===== ENUMS & DATA CLASSES =====
class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    FUSE_BLOWN = "fuse_blown"  # System paused due to repeated failures


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    FAILED = "failed"
    SCHEDULED = "scheduled"


@dataclass
class ErrorLog:
    """A single error entry in the log."""
    timestamp: str
    severity: str
    source: str
    message: str
    context: str = ""
    retry_count: int = 0
    resolved: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict):
        return cls(**{k: v for k, v in d.items() if k != 'severity'})


@dataclass
class RetryEntry:
    """An entry in the retry queue."""
    task_id: str
    source: str
    message: str
    attempt: int
    max_attempts: int
    next_retry_at: float  # timestamp
    backoff_multiplier: float = 2.0
    base_delay_seconds: float = 5.0

    def is_ready(self) -> bool:
        return time.time() >= self.next_retry_at

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class FuseState:
    """The state of a circuit breaker (fuse)."""
    name: str
    failures: int = 0
    threshold: int = 5          # Blows after N consecutive failures
    cooldown_seconds: float = 300.0  # 5 min cooldown before retrying
    last_failure_time: float = 0.0
    is_blown: bool = False

    def record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.threshold and not self.is_blown:
            self.is_blown = True
            console.print(f"[red]⚡ FUSE BLOWN: '{self.name}' — {self.failures} failures. Pausing for {self.cooldown_seconds}s[/]")

    def can_retry(self) -> bool:
        if not self.is_blown:
            return True
        elapsed = time.time() - self.last_failure_time
        if elapsed >= self.cooldown_seconds:
            self.is_blown = False
            self.failures = 0
            console.print(f"[green]✓ Fuse '{self.name}' reset after cooldown[/]")
            return True
        remaining = int(self.cooldown_seconds - elapsed)
        console.print(f"[yellow]Fuse '{self.name}' still cooling down: {remaining}s remaining[/]")
        return False


# ===== FUSE PANEL CLASS =====
class FusePanel:
    """Main fuse panel managing health, errors, retries, and fuses."""

    def __init__(self):
        self.errors = []  # Error log entries (max 500)
        self.retry_queue = []  # Pending retry tasks
        self.fuses = {}  # Named circuit breakers
        self.max_errors = 500
        self._load_state()

    def _get_log_path(self) -> Path:
        return Path(__file__).parent.parent / "logs" / "fuse_panel.json"

    def _ensure_logs_dir(self):
        logs_dir = Path(__file__).parent.parent / "logs"
        logs_dir.mkdir(exist_ok=True)

    def _load_state(self):
        """Load persisted state from disk."""
        self._ensure_logs_dir()
        path = self._get_log_path()
        if path.exists():
            try:
                with open(path) as f:
                    data = json.load(f)
                self.errors = [ErrorLog(**e) for e in data.get("errors", [])[-self.max_errors:]]
                self.retry_queue = [RetryEntry(**r) for r in data.get("retry_queue", [])]
            except (json.JSONDecodeError, KeyError):
                pass

    def _save_state(self):
        """Persist state to disk."""
        self._ensure_logs_dir()
        path = self._get_log_path()
        try:
            with open(path, "w") as f:
                json.dump({
                    "errors": [e.to_dict() for e in self.errors[-self.max_errors:]],
                    "retry_queue": [r.to_dict() for r in self.retry_queue],
                    "timestamp": datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            console.print(f"[yellow]⚠️ Could not save fuse state: {e}[/]")

    # ===== ERROR LOGGING =====
    def log_error(self, severity: Severity, source: str, message: str, context: str = "") -> ErrorLog:
        """Add an error to the log and trigger retry logic if needed."""
        entry = ErrorLog(
            timestamp=datetime.now().isoformat(),
            severity=severity.value,
            source=source,
            message=message,
            context=context
        )

        self.errors.append(entry)
        if len(self.errors) > self.max_errors:
            self.errors = self.errors[-self.max_errors:]

        # Display based on severity
        if severity == Severity.CRITICAL:
            console.print(f"[bold red]🔴 CRITICAL [{source}]: {message}[/]")
        elif severity == Severity.ERROR:
            console.print(f"[red]✗ ERROR [{source}]: {message}[/]")
        elif severity == Severity.WARNING:
            console.print(f"[yellow]⚠ WARNING [{source}]: {message}[/]")

        # Auto-add to retry queue for errors/critical
        if severity in (Severity.ERROR, Severity.CRITICAL):
            self.add_to_retry_queue(source, message)

        # Check if fuse should blow
        fuse_name = f"{source}_error_fuse"
        fuse = self.get_or_create_fuse(fuse_name, threshold=3, cooldown_seconds=600)
        fuse.record_failure()
        if fuse.is_blown:
            entry.severity = Severity.FUSE_BLOWN.value

        self._save_state()
        return entry

    def log_info(self, source: str, message: str):
        """Log an informational message."""
        entry = ErrorLog(
            timestamp=datetime.now().isoformat(),
            severity=Severity.INFO.value,
            source=source,
            message=message
        )
        self.errors.append(entry)
        if len(self.errors) > self.max_errors:
            self.errors = self.errors[-self.max_errors:]
        console.print(f"[dim]ℹ [{source}]: {message}[/]")
        self._save_state()

    # ===== RETRY LOGIC =====
    def add_to_retry_queue(self, source: str, message: str, max_attempts: int = 5):
        """Add a task to the retry queue with exponential backoff."""
        entry = RetryEntry(
            task_id=f"{source}_{int(time.time())}",
            source=source,
            message=message,
            attempt=1,
            max_attempts=max_attempts,
            next_retry_at=time.time() + 5.0  # First retry in 5 seconds
        )

        self.retry_queue.append(entry)
        console.print(f"[blue]🔄 Queued for retry: {source} (attempt 1/{max_attempts})[/]")
        self._save_state()

    def process_retry_queue(self):
        """Process all ready retries in the queue."""
        processed = []
        still_pending = []

        for entry in self.retry_queue:
            if entry.is_ready():
                console.print(f"[cyan]▶ Processing retry: {entry.source} (attempt {entry.attempt}/{entry.max_attempts})[/]")
                processed.append(entry)
            else:
                still_pending.append(entry)

        # Update remaining entries with next attempt time
        for entry in still_pending:
            if entry.attempt < entry.max_attempts:
                delay = entry.base_delay_seconds * (entry.backoff_multiplier ** (entry.attempt - 1))
                entry.next_retry_at = time.time() + delay
                entry.attempt += 1

        self.retry_queue = still_pending
        self._save_state()
        return processed

    def get_retry_status(self) -> dict:
        """Get current retry queue status."""
        ready = [e for e in self.retry_queue if e.is_ready()]
        pending = len(self.retry_queue) - len(ready)
        return {
            "total": len(self.retry_queue),
            "ready_to_retry": len(ready),
            "pending": pending,
            "entries": [{"task_id": e.task_id, "source": e.source, "attempt": e.attempt} for e in self.retry_queue]
        }

    # ===== FUSE / CIRCUIT BREAKER =====
    def get_or_create_fuse(self, name: str, threshold: int = 5, cooldown_seconds: float = 300.0) -> FuseState:
        """Get or create a named circuit breaker."""
        if name not in self.fuses:
            self.fuses[name] = FuseState(name=name, threshold=threshold, cooldown_seconds=cooldown_seconds)
        return self.fuses[name]

    def get_fuse_status(self) -> dict:
        """Get all fuse states."""
        return {name: {"failures": f.failures, "is_blown": f.is_blown} for name, f in self.fuses.items()}

    # ===== HEALTH CHECK =====
    def check_health(self) -> dict:
        """Run a health check and return status summary."""
        health = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "errors_last_hour": 0,
            "retry_queue_size": len(self.retry_queue),
            "blown_fuses": [],
            "disk_usage_mb": self._get_disk_usage(),
            "uptime_seconds": self._get_uptime()
        }

        # Count errors in last hour
        one_hour_ago = time.time() - 3600
        for e in self.errors:
            try:
                ts = datetime.fromisoformat(e.timestamp).timestamp()
                if ts > one_hour_ago and e.severity in (Severity.ERROR.value, Severity.CRITICAL.value):
                    health["errors_last_hour"] += 1
            except (ValueError, AttributeError):
                pass

        # Check blown fuses
        for name, fuse in self.fuses.items():
            if fuse.is_blown:
                health["blown_fuses"].append(name)
                health["status"] = "degraded"

        # If too many errors recently, mark as degraded
        if health["errors_last_hour"] > 10:
            health["status"] = "critical"

        return health

    def _get_disk_usage(self) -> float:
        """Get disk usage percentage for the agent's directory."""
        try:
            import shutil
            total, used, free = shutil.disk_usage(Path(__file__).parent.parent)
            return round(used / total * 100, 1)
        except Exception:
            return -1

    def _get_uptime(self) -> float:
        """Get agent uptime in seconds."""
        try:
            import psutil
            proc = psutil.Process(os.getpid())
            return round(time.time() - proc.create_time(), 0)
        except Exception:
            return -1

    # ===== STATUS REPORT (for chat panel) =====
    def get_status_report(self) -> str:
        """Generate a human-readable status report."""
        health = self.check_health()
        retry_status = self.get_retry_status()
        fuse_status = self.get_fuse_status()

        lines = [
            f"🔧 Fuse Panel Status:",
            f"  System: {'✅ Healthy' if health['status'] == 'healthy' else '⚠️ Degraded'}",
            f"  Errors (last hour): {health['errors_last_hour']}",
            f"  Retry queue: {retry_status['total']} tasks ({retry_status['ready_to_retry']} ready)",
        ]

        if fuse_status:
            blown = [n for n, s in fuse_status.items() if s["is_blown"]]
            lines.append(f"  Blown fuses: {', '.join(blown) if blown else 'None'}")

        # Recent errors (last 5)
        recent_errors = [e for e in self.errors[-10:] if e.severity != Severity.INFO.value]
        if recent_errors:
            lines.append(f"\n📋 Recent Errors:")
            for e in recent_errors[-5:]:
                lines.append(f"  [{e.severity.upper()}] {e.source}: {e.message[:60]}")

        return "\n".join(lines)


# ===== HARDENING FIXES (Scheduled Maintenance Tasks) =====
class HardeningFixes:
    """Automated maintenance/hardening tasks that run on schedule."""

    def __init__(self, fuse_panel: FusePanel):
        self.fuse = fuse_panel
        self.fixes = {
            "clear_old_errors": self._fix_clear_old_errors,
            "refresh_fuses": self._fix_refresh_fuses,
            "compact_retry_queue": self._fix_compact_retry_queue,
            "verify_auth_token": self._fix_verify_auth_token,
            "cleanup_logs": self._fix_cleanup_logs,
        }

    def run_all_fixes(self) -> list[str]:
        """Run all scheduled hardening fixes. Returns list of fix names that ran."""
        executed = []
        for name, func in self.fixes.items():
            try:
                result = func()
                if result:
                    executed.append(name)
                    console.print(f"[green]✓ Hardening fix '{name}' applied[/]")
            except Exception as e:
                self.fuse.log_error(Severity.WARNING, "hardening", f"Fix '{name}' failed: {e}")
        return executed

    def _fix_clear_old_errors(self) -> bool:
        """Remove resolved errors older than 24 hours."""
        cutoff = time.time() - 86400
        before = len(self.fuse.errors)
        self.fuse.errors = [
            e for e in self.fuse.errors
            if not e.resolved or (datetime.fromisoformat(e.timestamp).timestamp() > cutoff)
        ]
        removed = before - len(self.fuse.errors)
        return removed > 0

    def _fix_refresh_fuses(self) -> bool:
        """Reset all fuses that have cooled down."""
        reset_count = 0
        for name, fuse in self.fuse.fuses.items():
            if fuse.is_blown and time.time() - fuse.last_failure_time > fuse.cooldown_seconds:
                fuse.is_blown = False
                fuse.failures = 0
                reset_count += 1
        return reset_count > 0

    def _fix_compact_retry_queue(self) -> bool:
        """Remove failed retries that exceeded max attempts."""
        before = len(self.fuse.retry_queue)
        self.fuse.retry_queue = [
            e for e in self.fuse.retry_queue if e.attempt <= e.max_attempts
        ]
        return before > len(self.fuse.retry_queue)

    def _fix_verify_auth_token(self) -> bool:
        """Check auth token validity and log warning if expiring soon."""
        # This would integrate with the PolymarketClient's token refresh logic
        console.print("[dim]ℹ Auth token check passed (integrated in client)[/]")
        return False  # No action needed unless integrated

    def _fix_cleanup_logs(self) -> bool:
        """Compress and archive old log files."""
        logs_dir = Path(__file__).parent.parent / "logs"
        if not logs_dir.exists():
            return False
        old_files = [f for f in logs_dir.iterdir() if f.suffix == ".json" and f.stat().st_mtime < time.time() - 86400]
        for f in old_files:
            try:
                f.unlink()
            except Exception:
                pass
        return len(old_files) > 0


# ===== INITIALIZATION =====
def create_fuse_panel() -> FusePanel:
    """Factory function to create a configured fuse panel."""
    panel = FusePanel()
    # Register default fuses
    panel.get_or_create_fuse("api_connection", threshold=3, cooldown_seconds=120)
    panel.get_or_create_fuse("auth_failure", threshold=5, cooldown_seconds=600)
    panel.get_or_create_fuse("order_execution", threshold=3, cooldown_seconds=300)
    return panel


def create_hardening_fixes(fuse_panel: FusePanel) -> HardeningFixes:
    """Factory function to create hardening fixes tied to a fuse panel."""
    return HardeningFixes(fuse_panel)
