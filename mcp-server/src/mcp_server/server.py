"""PolyAgent MCP Server — Persistent Memory for Dev Lifecycle & Polymarket App.

This MCP server provides tools optimized for:
1. The PolyAgent development lifecycle (experiment tracking, strategy comparison)
2. The actual Polymarket application (market scanning, position management, orders)

Usage in LM Studio / Bionic:
  - Install: pip install -e F:/PolyMarket/mcp-server/
  - Configure in settings.json with the server command below
"""

import asyncio
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

# Import tools from both categories (aliased to avoid naming conflicts)
from .tools.dev_lifecycle.project_state import (
    get_project_state as _get_ps,
    set_project_state as _set_ps,
    scan_codebase_status as _scan_ps,
    get_all_project_states as _get_all_ps,
)
from .tools.dev_lifecycle.experiment_log import (
    log_experiment as _log_exp,
    update_experiment as _upd_exp,
    list_experiments as _list_exp,
    delete_experiment as _del_exp,
    compare_strategies as _compare_strat,
    get_experiment_summary as _get_exp_summ,
)
from .tools.polymarket.market_scan import (
    scan_markets,
    get_market_detail,
    search_markets,
)
from .tools.polymarket.position_manager import (
    get_positions,
    close_position,
    partial_close_position,
)
from .tools.polymarket.risk_dashboard import (
    get_risk_state,
    check_can_trade,
)
from .tools.polymarket.order_tools import (
    create_order,
    cancel_order,
    cancel_all_orders,
    preview_order,
)
from .tools.polymarket.portfolio_query import (
    get_portfolio_summary,
    get_account_balances,
    get_activities,
)

# Create the MCP server instance
mcp = FastMCP(
    name="polyagent-mcp-server",
    version="0.1.0",
    description=(
        "Persistent Memory MCP Server optimized for PolyAgent development lifecycle "
        "and Polymarket application integration."
    ),
)


# =============================================================================
# DEV LIFECYCLE TOOLS
# =============================================================================

@mcp.tool()
def get_project_state(key: str) -> dict[str, Any]:
    """Get a project state value by key. Returns the current state of the PolyAgent project."""
    return {"key": key, "value": _get_ps(key)}


@mcp.tool()
def set_project_state(key: str, value: str) -> dict[str, Any]:
    """Set a project state value (e.g., 'current_phase', 'active_strategy')."""
    result = _set_ps(key, value)
    return {"success": True, "key": key, "value": value}


@mcp.tool()
def scan_codebase_status() -> dict[str, Any]:
    """Scan the PolyAgent codebase and report which modules are complete vs skeleton."""
    return _scan_ps()


@mcp.tool()
def log_experiment(
    name: str,
    strategy: str,
    description: str = "",
    parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Log a new experiment run. Returns the experiment ID for later reference."""
    return _log_exp(name, strategy, description, parameters or {})


@mcp.tool()
def update_experiment(
    experiment_id: int,
    status: str = "",
    results: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Update an existing experiment's status and/or results."""
    return _upd_exp(experiment_id, status=status, results=results or {})


@mcp.tool()
def list_experiments(status_filter: str = "") -> dict[str, Any]:
    """List all logged experiments. Optional filter by status (running/completed/failed)."""
    return _list_exp(status=status_filter)


@mcp.tool()
def delete_experiment(experiment_id: int) -> dict[str, Any]:
    """Delete a logged experiment."""
    return _del_exp(experiment_id)


@mcp.tool()
def compare_strategies(
    exp_a_id: int,
    exp_b_id: int,
    notes: str = "",
    winner: str = "",
) -> dict[str, Any]:
    """Create a strategy comparison between two experiments."""
    return _compare_strat(exp_a_id, exp_b_id, notes=notes, winner=winner)


@mcp.tool()
def get_experiment_summary() -> dict[str, Any]:
    """Get a summary of all experiments (counts by status, strategies used)."""
    return _get_exp_summ()


@mcp.tool()
def get_all_project_states() -> dict[str, str]:
    """Get all project state key-value pairs as a flat dictionary."""
    return _get_all_ps()


# =============================================================================
# POLYMARKET APP TOOLS
# =============================================================================

@mcp.tool()
def scan_markets(
    limit: int = 50,
    category: str = "",
    min_volume_24h: float = 0,
    closed: bool = False,
) -> dict[str, Any]:
    """Scan Polymarket for active markets. Filters by category and minimum volume."""
    return scan_markets(limit=limit, category=category, min_volume=min_volume_24h, closed=closed)


@mcp.tool()
def get_market_detail(market_slug: str) -> dict[str, Any]:
    """Get detailed information about a specific Polymarket market by slug."""
    return get_market_detail(market_slug)


@mcp.tool()
def search_markets(query: str, limit: int = 20) -> dict[str, Any]:
    """Search Polymarket markets and events by keyword query."""
    return search_markets(query=query, limit=limit)


@mcp.tool()
def get_positions(market_slug: str = "") -> dict[str, Any]:
    """Get all open positions. Optionally filter by market slug."""
    return get_positions(market_slug=market_slug)


@mcp.tool()
def close_position(
    position_id: int | None = None,
    market_slug: str = "",
    reason: str = "manual",
) -> dict[str, Any]:
    """Close a specific position or all positions in a market."""
    return close_position(position_id=position_id, market_slug=market_slug, reason=reason)


@mcp.tool()
def partial_close_position(
    position_id: int | None = None,
    market_slug: str = "",
    close_pct: float = 0.5,
) -> dict[str, Any]:
    """Partially close a position (e.g., cash out 50% for guaranteed profit)."""
    return partial_close_position(position_id=position_id, market_slug=market_slug, close_pct=close_pct)


@mcp.tool()
def get_risk_state() -> dict[str, Any]:
    """Get the current risk state of the PolyAgent (budget, PnL, kill switch status)."""
    return get_risk_state()


@mcp.tool()
def check_can_trade(size_usdc: float = 0) -> dict[str, Any]:
    """Check if trading is allowed right now based on risk limits."""
    return check_can_trade(size_usdc=size_usdc)


@mcp.tool()
def create_order(
    market_slug: str,
    side: str,
    price: float,
    size_usdc: float,
    order_type: str = "LIMIT",
) -> dict[str, Any]:
    """Create a new order on Polymarket. Side: BUY or SELL."""
    return create_order(market_slug=market_slug, side=side, price=price, size_usdc=size_usdc, order_type=order_type)


@mcp.tool()
def cancel_order(order_id: str) -> dict[str, Any]:
    """Cancel a specific open order by its exchange-assigned ID."""
    return cancel_order(order_id=order_id)


@mcp.tool()
def cancel_all_orders(market_slug: str = "") -> dict[str, Any]:
    """Cancel all open orders. Optionally filter by market slug."""
    return cancel_all_orders(market_slug=market_slug)


@mcp.tool()
def preview_order(
    market_slug: str,
    side: str,
    price: float,
    size_usdc: float,
) -> dict[str, Any]:
    """Preview an order before submission to validate parameters and see expected fills."""
    return preview_order(market_slug=market_slug, side=side, price=price, size_usdc=size_usdc)


@mcp.tool()
def get_portfolio_summary() -> dict[str, Any]:
    """Get current portfolio summary: positions, balances, buying power."""
    return get_portfolio_summary()


@mcp.tool()
def get_account_balances() -> dict[str, Any]:
    """Get account balances including current balance and buying power."""
    return get_account_balances()


@mcp.tool()
def get_activities(limit: int = 50) -> dict[str, Any]:
    """Get recent trading activity (trades, resolutions, balance changes)."""
    return get_activities(limit=limit)


# =============================================================================
# UTILITY TOOLS
# =============================================================================

@mcp.tool()
def cache_stats() -> dict[str, Any]:
    """Get Polymarket cache statistics (entry count, keys, file size)."""
    from .persistence.polymarket_cache import get_polymarket_cache
    return get_polymarket_cache().get_stats()


@mcp.tool()
def clear_cache() -> dict[str, Any]:
    """Clear all Polymarket cached data."""
    from .persistence.polymarket_cache import get_polymarket_cache
    get_polymarket_cache().clear_all()
    return {"success": True, "message": "Cache cleared"}


# =============================================================================
# ENTRY POINT
# =============================================================================

def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
