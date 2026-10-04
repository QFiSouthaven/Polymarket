"""Experiment Log tools — track, compare, and analyze strategy experiments.

Provides:
- log_experiment: record a new experiment run with parameters and results
- update_experiment: update status/results of an existing experiment
- list_experiments: browse all logged experiments
- delete_experiment: remove an experiment entry
- compare_strategies: create side-by-side comparisons between two runs
"""

import json
from datetime import datetime, timezone
from typing import Any


def log_experiment(
    name: str,
    strategy: str,
    description: str = "",
    parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Log a new experiment run.

    Args:
        name: Human-readable experiment name (e.g., 'Momentum v2 - high volume markets')
        strategy: Strategy identifier (e.g., 'momentum', 'edge_detection', 'bundle_arbitrage')
        description: Brief description of what this experiment tests
        parameters: Dict of strategy parameters used in this run

    Returns:
        dict with experiment_id and status
    """
    from ..persistence.dev_state import DevStateDB
    db = DevStateDB()

    exp_id = db.log_experiment(
        name=name,
        strategy=strategy,
        description=description,
        parameters=parameters or {},
        results={},
        status="running",
    )

    return {
        "success": True,
        "experiment_id": exp_id,
        "name": name,
        "strategy": strategy,
        "status": "running",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def update_experiment(
    experiment_id: int,
    status: str = "",
    results: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Update an existing experiment's status and/or results.

    Args:
        experiment_id: The ID returned from log_experiment
        status: New status ('running', 'completed', 'failed')
        results: Dict of results (e.g., {'pnl': 123.45, 'trades': 15})

    Returns:
        dict with updated experiment info
    """
    from ..persistence.dev_state import DevStateDB
    db = DevStateDB()

    # Get current state first
    existing = db.get_experiment(experiment_id)
    if not existing:
        return {"success": False, "error": f"Experiment {experiment_id} not found"}

    updates = {}
    if status:
        updates["status"] = status
    if results is not None:
        updates["results"] = results

    db.update_experiment(experiment_id, **updates)

    updated = db.get_experiment(experiment_id)
    return {
        "success": True,
        "experiment_id": experiment_id,
        "status": updated["status"],
        "results": updated["results"],
    }


def list_experiments(status: str = "") -> dict[str, Any]:
    """List all logged experiments.

    Args:
        status: Optional filter ('running', 'completed', 'failed') or '' for all

    Returns:
        dict with list of experiments and count
    """
    from ..persistence.dev_state import DevStateDB
    db = DevStateDB()

    if status:
        experiments = db.list_experiments(status=status, limit=100)
    else:
        experiments = db.list_experiments(limit=100)

    return {
        "count": len(experiments),
        "experiments": [
            {
                "id": e["id"],
                "name": e["name"],
                "strategy": e["strategy"],
                "status": e["status"],
                "description": e.get("description", ""),
                "parameters": e.get("parameters", {}),
                "results": e.get("results", {}),
                "created_at": e["created_at"],
            }
            for e in experiments
        ],
    }


def delete_experiment(experiment_id: int) -> dict[str, Any]:
    """Delete a logged experiment.

    Args:
        experiment_id: The ID of the experiment to delete

    Returns:
        dict with success status
    """
    from ..persistence.dev_state import DevStateDB
    db = DevStateDB()

    # Verify it exists first
    existing = db.get_experiment(experiment_id)
    if not existing:
        return {"success": False, "error": f"Experiment {experiment_id} not found"}

    deleted = db.delete_experiment(experiment_id)
    return {
        "success": True,
        "deleted_id": experiment_id,
        "name": existing["name"],
    }


def compare_strategies(
    exp_a_id: int,
    exp_b_id: int,
    notes: str = "",
    winner: str = "",
) -> dict[str, Any]:
    """Create a strategy comparison between two experiments.

    Args:
        exp_a_id: First experiment ID (e.g., baseline strategy)
        exp_b_id: Second experiment ID (e.g., new variant)
        notes: Comparison notes (what changed, what to look for)
        winner: Which was better ('a', 'b', or '' if inconclusive)

    Returns:
        dict with comparison details
    """
    from ..persistence.dev_state import DevStateDB
    db = DevStateDB()

    exp_a = db.get_experiment(exp_a_id)
    exp_b = db.get_experiment(exp_b_id)

    if not exp_a:
        return {"success": False, "error": f"Experiment {exp_a_id} not found"}
    if not exp_b:
        return {"success": False, "error": f"Experiment {exp_b_id} not found"}

    comp_id = db.create_comparison(exp_a_id, exp_b_id, notes=notes, winner=winner)

    # Build comparison summary
    results_a = exp_a.get("results", {})
    results_b = exp_b.get("results", {})

    comparison = {
        "experiment_a": {
            "id": exp_a["id"],
            "name": exp_a["name"],
            "strategy": exp_a["strategy"],
            "parameters": exp_a.get("parameters", {}),
            "results": results_a,
        },
        "experiment_b": {
            "id": exp_b["id"],
            "name": exp_b["name"],
            "strategy": exp_b["strategy"],
            "parameters": exp_b.get("parameters", {}),
            "results": results_b,
        },
        "notes": notes,
        "winner": winner,
    }

    # Auto-generate comparison highlights if both have PnL data
    pnl_a = results_a.get("pnl_usdc")
    pnl_b = results_b.get("pnl_usdc")
    if pnl_a is not None and pnl_b is not None:
        comparison["auto_comparison"] = {
            "pnl_difference": round(pnl_b - pnl_a, 2),
            "better_pnl": "b" if pnl_b > pnl_a else ("a" if pnl_a > pnl_b else "tie"),
        }

    return {
        "success": True,
        "comparison_id": comp_id,
        "comparison": comparison,
    }


def get_experiment_details(experiment_id: int) -> dict[str, Any]:
    """Get full details of a single experiment.

    Args:
        experiment_id: The ID of the experiment

    Returns:
        dict with complete experiment data
    """
    from ..persistence.dev_state import DevStateDB
    db = DevStateDB()

    exp = db.get_experiment(experiment_id)
    if not exp:
        return {"success": False, "error": f"Experiment {experiment_id} not found"}

    # Get related comparisons
    comparisons = db.get_comparisons(limit=10)
    related = [c for c in comparisons if c["experiment_a_id"] == experiment_id or c["experiment_b_id"] == experiment_id]

    return {
        "success": True,
        "experiment": exp,
        "related_comparisons": len(related),
    }


def get_experiment_summary() -> dict[str, Any]:
    """Get a summary of all experiments (counts by status, strategies used)."""
    from ..persistence.dev_state import DevStateDB
    db = DevStateDB()

    all_exps = db.list_experiments(limit=1000)
    if not all_exps:
        return {"total": 0, "by_status": {}, "by_strategy": {}}

    by_status = {}
    by_strategy = {}
    for exp in all_exps:
        status = exp["status"]
        strategy = exp["strategy"]
        by_status[status] = by_status.get(status, 0) + 1
        by_strategy[strategy] = by_strategy.get(strategy, 0) + 1

    return {
        "total": len(all_exps),
        "by_status": by_status,
        "by_strategy": by_strategy,
        "most_recent": all_exps[0]["name"] if all_exps else None,
    }
