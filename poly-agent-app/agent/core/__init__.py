"""
PolyAgent Core - Operational Resilience Layer
==============================================
- Fuse Panel: Error logging, retry queues, circuit breakers
- Heartbeat Harness: Periodic health checks, automated maintenance
- Message Board: Task/to-do management for the agent

Usage:
    from core.fuse_panel import create_fuse_panel, HardeningFixes
    from core.heartbeat import create_heartbeat, create_message_board
"""

from .fuse_panel import FusePanel, HardeningFixes, Severity, FuseState, ErrorLog, RetryEntry, create_fuse_panel
from .heartbeat import HeartbeatHarness, MessageBoard, Task, create_heartbeat, create_message_board

__all__ = [
    "FusePanel", "HardeningFixes", "Severity", "FuseState", "ErrorLog", "RetryEntry",
    "HeartbeatHarness", "MessageBoard", "Task",
    "create_fuse_panel", "create_heartbeat", "create_message_board"
]
