"""Project State tool — tracks PolyAgent project state and codebase status.

Provides:
- get_project_state / set_project_state: key-value store for project metadata
- scan_codebase_status: scans poly-agent/src/ to report module completion status
"""

import os
from pathlib import Path
from typing import Any

# Resolve workspace root from this file's location
_WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def get_project_state(key: str) -> str | None:
    """Get a project state value by key."""
    from ..persistence.dev_state import DevStateDB
    db = DevStateDB()
    return db.get_project_state(key)


def set_project_state(key: str, value: str) -> dict[str, Any]:
    """Set a project state value. Common keys: 'current_phase', 'active_strategy', 'deploy_version'."""
    from ..persistence.dev_state import DevStateDB
    db = DevStateDB()
    db.set_project_state(key, value)
    return {"success": True, "key": key, "value": value}


def scan_codebase_status() -> dict[str, Any]:
    """Scan the PolyAgent codebase and report which modules are complete vs skeleton.

    Checks each directory under poly-agent/src/ for:
    - __init__.py presence (module boundary)
    - .py file count (skeleton = 0-1 files, partial = 2-3, complete = 4+)
    - Key files existence (engine.py, risk_manager.py, etc.)

    Returns a structured report of all modules.
    """
    src_dir = _WORKSPACE_ROOT / "poly-agent" / "src"
    if not src_dir.exists():
        return {"error": f"Source directory not found: {src_dir}"}

    results = []
    total_modules = 0
    complete_count = 0
    partial_count = 0
    skeleton_count = 0

    for item in sorted(src_dir.iterdir()):
        if not item.is_dir():
            continue

        module_name = item.name
        py_files = list(item.rglob("*.py"))
        init_file = item / "__init__.py"

        # Determine status based on file count and key files
        py_count = len(py_files)
        has_init = init_file.exists()

        if py_count == 0:
            status = "skeleton"
            skeleton_count += 1
        elif py_count <= 2 or not has_init:
            status = "partial"
            partial_count += 1
        else:
            # Check for key implementation files
            key_files = ["__init__.py"]
            if item.name == "poly_agent":
                key_files.extend(["engine.py", "risk_manager.py", "position_tracker.py"])
            elif item.name in ("strategies", "execution"):
                key_files.append("__init__.py")

            has_key_files = all((item / f).exists() for f in key_files)
            if has_key_files and py_count >= 4:
                status = "complete"
                complete_count += 1
            else:
                status = "partial"
                partial_count += 1

        total_modules += 1

        results.append({
            "module": module_name,
            "path": str(item.relative_to(_WORKSPACE_ROOT)),
            "status": status,
            "py_file_count": py_count,
            "has_init": has_init,
            "key_files_present": [f for f in key_files if (item / f).exists()],
        })

    return {
        "workspace_root": str(_WORKSPACE_ROOT),
        "total_modules": total_modules,
        "complete": complete_count,
        "partial": partial_count,
        "skeleton": skeleton_count,
        "modules": results,
        "summary": f"{complete_count}/{total_modules} modules complete",
    }


def get_all_project_states() -> dict[str, str]:
    """Get all project state key-value pairs."""
    from ..persistence.dev_state import DevStateDB
    db = DevStateDB()
    return db.get_all_project_states()
