"""Dev State DB — SQLite persistence for development lifecycle tracking.

Stores: project state, experiment logs, strategy comparisons, codebase status.
All data is local to the workspace and survives MCP server restarts.
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


class DevStateDB:
    """SQLite database for development lifecycle state."""

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            # Default to workspace-local SQLite file
            self.db_path = Path(__file__).resolve().parent.parent.parent / "dev_state.db"
        else:
            self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self) -> sqlite3.Connection:
        """Get or create the database connection."""
        if self._conn is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
            self._init_tables()
        return self._conn

    def _init_tables(self):
        """Create tables if they don't exist."""
        conn = self.connect()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS project_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS experiment_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                strategy TEXT NOT NULL,
                description TEXT,
                parameters TEXT NOT NULL,
                results TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'running',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS strategy_comparison (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_a_id INTEGER REFERENCES experiment_log(id),
                experiment_b_id INTEGER REFERENCES experiment_log(id),
                comparison_notes TEXT,
                winner TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS codebase_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                module_path TEXT UNIQUE NOT NULL,
                status TEXT NOT NULL DEFAULT 'skeleton',
                last_checked TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                notes TEXT
            );

            CREATE TABLE IF NOT EXISTS deployment_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT NOT NULL,
                environment TEXT NOT NULL,
                status TEXT NOT NULL,
                details TEXT,
                deployed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_experiment_status ON experiment_log(status);
            CREATE INDEX IF NOT EXISTS idx_codebase_module ON codebase_status(module_path);
        """)
        conn.commit()

    # --- Project State ---

    def get_project_state(self, key: str) -> Optional[str]:
        """Get a project state value by key."""
        conn = self.connect()
        row = conn.execute(
            "SELECT value FROM project_state WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else None

    def set_project_state(self, key: str, value: str) -> None:
        """Set a project state value."""
        conn = self.connect()
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT OR REPLACE INTO project_state (key, value, updated_at) VALUES (?, ?, ?)",
            (key, value, now),
        )
        conn.commit()

    def get_all_project_states(self) -> dict[str, str]:
        """Get all project state key-value pairs."""
        conn = self.connect()
        rows = conn.execute("SELECT key, value FROM project_state").fetchall()
        return {row["key"]: row["value"] for row in rows}

    # --- Experiment Logging ---

    def log_experiment(
        self,
        name: str,
        strategy: str,
        description: Optional[str] = None,
        parameters: dict[str, Any] | None = None,
        results: dict[str, Any] | None = None,
        status: str = "running",
    ) -> int:
        """Log a new experiment. Returns the experiment ID."""
        conn = self.connect()
        now = datetime.now(timezone.utc).isoformat()
        cursor = conn.execute(
            """INSERT INTO experiment_log (name, strategy, description, parameters, results, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (name, strategy, description, json.dumps(parameters or {}), json.dumps(results or {}), status, now),
        )
        conn.commit()
        return cursor.lastrowid

    def update_experiment(self, experiment_id: int, **kwargs) -> None:
        """Update an existing experiment's fields."""
        conn = self.connect()
        updates = []
        params = []
        for key, value in kwargs.items():
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            updates.append(f"{key} = ?")
            params.append(value)
        params.append(datetime.now(timezone.utc).isoformat())
        params.append(experiment_id)
        conn.execute(
            f"UPDATE experiment_log SET {', '.join(updates)}, updated_at = ? WHERE id = ?",
            params,
        )
        conn.commit()

    def get_experiment(self, experiment_id: int) -> Optional[dict]:
        """Get a single experiment by ID."""
        conn = self.connect()
        row = conn.execute("SELECT * FROM experiment_log WHERE id = ?", (experiment_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["parameters"] = json.loads(d["parameters"])
        d["results"] = json.loads(d["results"])
        return d

    def list_experiments(self, status: Optional[str] = None, limit: int = 50) -> list[dict]:
        """List experiments with optional status filter."""
        conn = self.connect()
        if status:
            rows = conn.execute(
                "SELECT * FROM experiment_log WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM experiment_log ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def delete_experiment(self, experiment_id: int) -> bool:
        """Delete an experiment."""
        conn = self.connect()
        cursor = conn.execute("DELETE FROM experiment_log WHERE id = ?", (experiment_id,))
        conn.commit()
        return cursor.rowcount > 0

    # --- Strategy Comparison ---

    def create_comparison(self, exp_a: int, exp_b: int, notes: str = "", winner: str = "") -> int:
        """Create a strategy comparison between two experiments."""
        conn = self.connect()
        now = datetime.now(timezone.utc).isoformat()
        cursor = conn.execute(
            "INSERT INTO strategy_comparison (experiment_a_id, experiment_b_id, comparison_notes, winner, created_at) VALUES (?, ?, ?, ?, ?)",
            (exp_a, exp_b, notes, winner, now),
        )
        conn.commit()
        return cursor.lastrowid

    def get_comparisons(self, limit: int = 20) -> list[dict]:
        """Get strategy comparisons."""
        conn = self.connect()
        rows = conn.execute(
            "SELECT * FROM strategy_comparison ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(row) for row in rows]

    # --- Codebase Status ---

    def update_codebase_status(self, module_path: str, status: str, notes: str = "") -> None:
        """Update the status of a codebase module."""
        conn = self.connect()
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT OR REPLACE INTO codebase_status (module_path, status, last_checked, notes) VALUES (?, ?, ?, ?)",
            (module_path, status, now, notes),
        )
        conn.commit()

    def get_codebase_status(self, module_path: str) -> Optional[dict]:
        """Get the status of a specific module."""
        conn = self.connect()
        row = conn.execute(
            "SELECT * FROM codebase_status WHERE module_path = ?", (module_path,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        return d

    def get_all_codebase_status(self) -> list[dict]:
        """Get status of all tracked modules."""
        conn = self.connect()
        rows = conn.execute("SELECT * FROM codebase_status ORDER BY module_path").fetchall()
        return [dict(row) for row in rows]

    # --- Deployment Log ---

    def log_deployment(self, version: str, environment: str, status: str, details: str = "") -> int:
        """Log a deployment event."""
        conn = self.connect()
        now = datetime.now(timezone.utc).isoformat()
        cursor = conn.execute(
            "INSERT INTO deployment_log (version, environment, status, details, deployed_at) VALUES (?, ?, ?, ?, ?)",
            (version, environment, status, details, now),
        )
        conn.commit()
        return cursor.lastrowid

    def get_deployments(self, limit: int = 20) -> list[dict]:
        """Get recent deployments."""
        conn = self.connect()
        rows = conn.execute(
            "SELECT * FROM deployment_log ORDER BY deployed_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(row) for row in rows]

    # --- Helpers ---

    def _row_to_dict(self, row: sqlite3.Row) -> dict:
        """Convert a SQLite row to a dict with JSON parsing."""
        d = dict(row)
        if "parameters" in d and isinstance(d["parameters"], str):
            try:
                d["parameters"] = json.loads(d["parameters"])
            except (json.JSONDecodeError, TypeError):
                pass
        if "results" in d and isinstance(d["results"], str):
            try:
                d["results"] = json.loads(d["results"])
            except (json.JSONDecodeError, TypeError):
                pass
        return d

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
