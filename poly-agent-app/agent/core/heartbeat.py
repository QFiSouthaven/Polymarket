#!/usr/bin/env python3
"""
Heartbeat Harness - Periodic Health Monitoring & Automated Maintenance
======================================================================
Runs on a configurable interval (default: 60s) to:
- Check system health (API connectivity, auth token, disk space)
- Process retry queues
- Run scheduled hardening fixes
- Monitor agent performance and alert on anomalies

This is the "nervous system" of PolyAgent — it keeps everything healthy.
"""

import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


class HeartbeatHarness:
    """The heartbeat harness that runs periodic health checks and maintenance."""

    def __init__(self, fuse_panel, agent=None):
        self.fuse = fuse_panel
        self.agent = agent  # Reference to PolyAgent (for context)
        self.interval_seconds = 60  # Default: check every 60 seconds
        self.running = False
        self.last_check_time = time.time()
        self.check_count = 0
        self.consecutive_failures = 0

        # Health thresholds
        self.max_consecutive_api_failures = 3
        self.disk_usage_warning_pct = 85.0
        self.memory_warning_mb = 2048  # 2GB warning threshold

        # Scheduled tasks (name -> interval_seconds)
        self.scheduled_tasks = {
            "hardening_fixes": 600,       # Run hardening every 10 minutes
            "retry_processing": 30,         # Process retries every 30s
            "health_report": 300,           # Full health report every 5 min
            "log_compaction": 3600,         # Compact logs every hour
        }
        self._task_last_run = {name: time.time() for name in self.scheduled_tasks}

    def start(self):
        """Start the heartbeat loop."""
        self.running = True
        console.print(Panel("[bold green]❤️ Heartbeat Harness Started[/]", border_style="green"))
        console.print(f"[dim]  Interval: {self.interval_seconds}s | Tasks: {list(self.scheduled_tasks.keys())}[/]")

    def stop(self):
        """Stop the heartbeat loop."""
        self.running = False
        console.print("[yellow]⏹ Heartbeat Harness stopped.[/]")

    def run_cycle(self) -> dict:
        """Run one complete heartbeat cycle. Returns health summary."""
        if not self.running:
            return {"status": "stopped"}

        self.check_count += 1
        now = time.time()
        results = {
            "check_number": self.check_count,
            "timestamp": datetime.now().isoformat(),
            "checks": {},
            "actions_taken": [],
        }

        # 1. Health check (always runs)
        health = self.fuse.check_health()
        results["checks"]["system_health"] = health

        if health["status"] == "critical":
            console.print("[bold red]🔴 CRITICAL: System health is critical! Pausing agent.[/]")
            if self.agent and hasattr(self.agent, 'stop'):
                self.agent.stop()

        # 2. Process retry queue (every 30s)
        if now - self._task_last_run["retry_processing"] >= self.scheduled_tasks["retry_processing"]:
            retries = self.fuse.process_retry_queue()
            results["checks"]["retries_processed"] = len(retries)
            if retries:
                results["actions_taken"].append(f"Processed {len(retries)} retry tasks")
            self._task_last_run["retry_processing"] = now

        # 3. Run hardening fixes (every 10 min)
        from core.fuse_panel import HardeningFixes
        if now - self._task_last_run["hardening_fixes"] >= self.scheduled_tasks["hardening_fixes"]:
            fixer = HardeningFixes(self.fuse)
            executed = fixer.run_all_fixes()
            results["checks"]["hardening_applied"] = len(executed)
            if executed:
                results["actions_taken"].append(f"Applied {len(executed)} hardening fixes")
            self._task_last_run["hardening_fixes"] = now

        # 4. Full health report (every 5 min)
        if now - self._task_last_run["health_report"] >= self.scheduled_tasks["health_report"]:
            report = self.fuse.get_status_report()
            console.print(Panel(report, title="🔧 Heartbeat Health Report", border_style="blue"))
            results["checks"]["full_report_generated"] = True
            self._task_last_run["health_report"] = now

        # 5. Log compaction (every hour)
        if now - self._task_last_run["log_compaction"] >= self.scheduled_tasks["log_compaction"]:
            logs_dir = Path(__file__).parent.parent / "logs"
            if logs_dir.exists():
                old_files = [f for f in logs_dir.iterdir()
                           if f.suffix == ".json" and f.stat().st_mtime < now - 86400]
                for f in old_files:
                    try:
                        f.unlink()
                        results["actions_taken"].append(f"Removed old log: {f.name}")
                    except Exception:
                        pass
            self._task_last_run["log_compaction"] = now

        # 6. Check API connectivity (if agent has client)
        if self.agent and hasattr(self.agent, 'client'):
            api_ok = self._check_api_connectivity()
            results["checks"]["api_connectivity"] = "ok" if api_ok else "failed"
            if not api_ok:
                self.consecutive_failures += 1
                self.fuse.log_error(
                    "error", "heartbeat",
                    f"API connectivity check failed (consecutive: {self.consecutive_failures})"
                )
                if self.consecutive_failures >= self.max_consecutive_api_failures:
                    console.print("[bold red]⚡ API unreachable for too long — agent paused![/]")
                    if hasattr(self.agent, 'stop'):
                        self.agent.stop()
            else:
                self.consecutive_failures = 0

        # 7. Disk space check
        disk_pct = health.get("disk_usage_mb", -1)
        if disk_pct > 0 and disk_pct > self.disk_usage_warning_pct:
            console.print(f"[yellow]⚠️ Disk usage at {disk_pct}% — approaching warning threshold[/]")

        return results

    def _check_api_connectivity(self) -> bool:
        """Check if the Polymarket API is reachable."""
        try:
            import requests
            resp = requests.get(
                "https://api.prod.polymarketexchange.com/v1/health",
                timeout=5,
                headers={"Content-Type": "application/json"}
            )
            return resp.status_code in (200, 401)  # 401 means API is up but needs auth
        except Exception:
            return False

    def get_status(self) -> dict:
        """Get current heartbeat status for the UI."""
        return {
            "running": self.running,
            "check_count": self.check_count,
            "interval_seconds": self.interval_seconds,
            "consecutive_failures": self.consecutive_failures,
            "scheduled_tasks": {name: int(time.time() - last) for name, last in self._task_last_run.items()},
        }

    def add_scheduled_task(self, name: str, interval_seconds: int):
        """Add a new scheduled task."""
        self.scheduled_tasks[name] = interval_seconds
        self._task_last_run[name] = time.time()
        console.print(f"[green]✓ Scheduled task '{name}' added (every {interval_seconds}s)[/]")

    def remove_scheduled_task(self, name: str):
        """Remove a scheduled task."""
        if name in self.scheduled_tasks:
            del self.scheduled_tasks[name]
            del self._task_last_run[name]
            console.print(f"[yellow]Removed scheduled task '{name}'[/]")


# ===== MESSAGE BOARD / TO-DO LIST SYSTEM =====
class MessageBoard:
    """A message board / to-do list where the agent posts tasks and tracks them."""

    def __init__(self):
        self.tasks = []  # List of Task objects
        self.max_tasks = 200
        self._load()

    def _get_path(self) -> Path:
        return Path(__file__).parent.parent / "logs" / "message_board.json"

    def _ensure_dir(self):
        logs_dir = Path(__file__).parent.parent / "logs"
        logs_dir.mkdir(exist_ok=True)

    def _load(self):
        self._ensure_dir()
        path = self._get_path()
        if path.exists():
            try:
                with open(path) as f:
                    data = json.load(f)
                for t in data.get("tasks", [])[-self.max_tasks:]:
                    self.tasks.append(Task.from_dict(t))
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        self._ensure_dir()
        path = self._get_path()
        try:
            with open(path, "w") as f:
                json.dump({"tasks": [t.to_dict() for t in self.tasks[-self.max_tasks:]]}, f, indent=2)
        except Exception as e:
            console.print(f"[yellow]⚠️ Could not save message board: {e}[/]")

    def add_task(self, title: str, priority: int = 5, category: str = "general",
                 due_in_seconds: Optional[int] = None, notes: str = "") -> 'Task':
        """Add a new task to the board."""
        now = time.time()
        task = Task(
            id=f"task_{int(now)}_{len(self.tasks)}",
            title=title,
            priority=priority,  # 1 (highest) to 10 (lowest)
            category=category,
            status="pending",
            created_at=datetime.now().isoformat(),
            due_at=(datetime.fromtimestamp(now + due_in_seconds).isoformat() if due_in_seconds else None),
            notes=notes
        )
        self.tasks.append(task)
        self._save()

        # Display based on priority
        if priority <= 3:
            console.print(f"[bold red]📌 HIGH PRIORITY TASK: {title}[/]")
        elif priority <= 5:
            console.print(f"[yellow]📋 Task added: {title}[/]")
        else:
            console.print(f"[dim]Task added: {title}[/]")

        return task

    def add_agent_task(self, agent_command: str) -> 'Task':
        """Add a task that the agent should execute (e.g., from chat commands)."""
        task = self.add_task(
            title=f"Agent command: '{agent_command}'",
            priority=3 if "scan" in agent_command.lower() else 7,
            category="agent_action",
            notes=f"Command received via chat panel"
        )

        # Execute high-priority tasks immediately
        if task.priority <= 3 and task.status == "pending":
            task.status = "in_progress"
            self._save()
            console.print(f"[cyan]▶ Executing agent task: {agent_command}[/]")
            # In production, this would call the agent's command handler
            return task

        return task

    def get_pending_tasks(self) -> list['Task']:
        """Get all pending tasks sorted by priority (highest first)."""
        pending = [t for t in self.tasks if t.status == "pending"]
        # Check due dates and escalate overdue tasks
        now = time.time()
        for task in pending:
            if task.due_at:
                try:
                    due_ts = datetime.fromisoformat(task.due_at).timestamp()
                    if due_ts < now:
                        task.priority = max(1, task.priority - 2)  # Escalate overdue tasks
                except (ValueError, AttributeError):
                    pass

        return sorted(pending, key=lambda t: t.priority)

    def get_task_summary(self) -> str:
        """Get a summary of the message board."""
        pending = self.get_pending_tasks()
        in_progress = [t for t in self.tasks if t.status == "in_progress"]
        done = len([t for t in self.tasks if t.status == "done"])

        lines = [f"📋 Message Board ({len(self.tasks)} total tasks):"]
        lines.append(f"  Pending: {len(pending)} | In Progress: {len(in_progress)} | Done: {done}")

        # Show top pending tasks by priority
        if pending:
            lines.append("\n  Top Priority Tasks:")
            for t in pending[:5]:
                due_str = f" (due soon!)" if t.due_at else ""
                lines.append(f"    [{t.priority}] {t.title}{due_str}")

        return "\n".join(lines)

    def complete_task(self, task_id: str) -> bool:
        """Mark a task as done."""
        for task in self.tasks:
            if task.id == task_id and task.status != "done":
                task.status = "done"
                task.completed_at = datetime.now().isoformat()
                self._save()
                console.print(f"[green]✓ Task completed: {task.title}[/]")
                return True
        return False

    def fail_task(self, task_id: str) -> bool:
        """Mark a task as failed."""
        for task in self.tasks:
            if task.id == task_id and task.status != "failed":
                task.status = "failed"
                task.failed_at = datetime.now().isoformat()
                self._save()
                console.print(f"[red]✗ Task failed: {task.title}[/]")
                return True
        return False


@dataclass
class Task:
    """A single message board task."""
    id: str
    title: str
    priority: int  # 1 (highest) to 10 (lowest)
    category: str = "general"
    status: str = "pending"
    created_at: str = ""
    due_at: Optional[str] = None
    completed_at: Optional[str] = None
    failed_at: Optional[str] = None
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id, "title": self.title, "priority": self.priority,
            "category": self.category, "status": self.status,
            "created_at": self.created_at, "due_at": self.due_at,
            "completed_at": self.completed_at, "failed_at": self.failed_at,
            "notes": self.notes
        }

    @classmethod
    def from_dict(cls, d: dict):
        return cls(**{k: v for k, v in d.items()})


# ===== INITIALIZATION =====
def create_heartbeat(fuse_panel, agent=None) -> HeartbeatHarness:
    """Factory to create a configured heartbeat harness."""
    hb = HeartbeatHarness(fuse_panel=fuse_panel, agent=agent)
    return hb


def create_message_board() -> MessageBoard:
    """Factory to create a message board."""
    return MessageBoard()
