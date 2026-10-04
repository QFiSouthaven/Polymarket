"""Position Manager tools — manage open positions on Polymarket.

Uses the existing PositionTracker and PolymarketExecutor from poly-agent/src/poly_agent/
with caching via PolymarketCache for performance.

Provides:
- get_positions: list all open positions (optionally filtered by market)
- close_position: close a specific position or all in a market
- partial_close_position: cash out a percentage of a position
"""

import asyncio
from typing import Any


def _get_executor() -> "PolymarketExecutor":
    """Get the authenticated Polymarket executor from poly-agent."""
    import sys
    workspace_root = __file__.resolve().parent.parent.parent.parent
    agent_src = workspace_root / "poly-agent" / "src"
    if str(agent_src) not in sys.path:
        sys.path.insert(0, str(agent_src))

    # Load config to get auth settings
    import yaml
    config_path = workspace_root / "poly-agent" / "config.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    from poly_agent.execution.executor import PolymarketExecutor
    return PolymarketExecutor(auth_config=config.get("auth", {}))


def _get_position_tracker() -> Any:
    """Get the position tracker instance."""
    import sys
    workspace_root = __file__.resolve().parent.parent.parent.parent
    agent_src = workspace_root / "poly-agent" / "src"
    if str(agent_src) not in sys.path:
        sys.path.insert(0, str(agent_src))

    import yaml
    config_path = workspace_root / "poly-agent" / "config.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    from poly_agent.risk_manager import RiskManager
    from poly_agent.position_tracker import PositionTracker

    risk_mgr = RiskManager(config)
    return PositionTracker(config, risk_mgr)


def _get_cache() -> Any:
    """Get the polymarket cache singleton."""
    from ..persistence.polymarket_cache import get_polymarket_cache
    return get_polymarket_cache()


def get_positions(market_slug: str = "") -> dict[str, Any]:
    """Get all open positions. Optionally filter by market slug.

    Args:
        market_slug: Optional filter to show only positions in a specific market

    Returns:
        dict with list of positions and summary stats
    """
    try:
        # Check cache first
        cached = _get_cache().get_cached_positions()
        if cached:
            if market_slug:
                filtered = [p for p in cached if p.get("market_slug") == market_slug]
                return {"success": True, "source": "cache", "positions": filtered}
            return {"success": True, "source": "cache", "positions": cached}

        # Get positions from Polymarket API via executor
        executor = _get_executor()
        portfolio = asyncio.get_event_loop().run_until_complete(executor.get_portfolio())

        positions = portfolio.get("positions", [])

        # Filter by market slug if specified
        if market_slug:
            positions = [p for p in positions if p.get("marketSlug") == market_slug]

        # Calculate summary stats
        total_pnl = sum(p.get("unrealizedPnl", 0) or p.get("unrealized_pnl", 0) for p in positions)
        total_value = sum(p.get("currentValue", 0) or p.get("current_value", 0) for p in positions)

        result = {
            "success": True,
            "source": "live",
            "positions": positions,
            "summary": {
                "total_positions": len(positions),
                "unrealized_pnl_usdc": round(total_pnl, 2),
                "total_position_value_usdc": round(total_value, 2),
            },
        }

        # Cache the result
        _get_cache().set_cached_positions(positions)

        return result

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "positions": [],
        }


def close_position(
    position_id: int | None = None,
    market_slug: str = "",
    reason: str = "manual",
) -> dict[str, Any]:
    """Close a specific position or all positions in a market.

    Args:
        position_id: Specific position ID to close (if provided, overrides market_slug)
        market_slug: Close ALL positions in this market (used if position_id not given)
        reason: Reason for closing (e.g., 'take_profit', 'stop_loss', 'manual')

    Returns:
        dict with close result details
    """
    try:
        executor = _get_executor()

        # Get current positions first
        portfolio = asyncio.get_event_loop().run_until_complete(executor.get_portfolio())
        positions = portfolio.get("positions", [])

        if position_id is not None:
            # Close specific position by ID
            target_positions = [p for p in positions if str(p.get("id")) == str(position_id)]
            if not target_positions:
                return {"success": False, "error": f"Position {position_id} not found"}

        elif market_slug:
            # Close all positions in this market
            target_positions = [p for p in positions if p.get("marketSlug") == market_slug]
            if not target_positions:
                return {"success": False, "error": f"No positions found in market '{market_slug}'"}

        else:
            # No filter specified — close all open positions
            target_positions = positions
            reason = "close_all"

        results = []
        for pos in target_positions:
            # Use the Close Position Order endpoint (polymarket.us API)
            market_slug_val = pos.get("marketSlug", "")
            side = pos.get("side", "BUY")  # Opposite of current position to close

            try:
                result = asyncio.get_event_loop().run_until_complete(
                    executor._place_order(market_slug_val, side.lower(), 1.0, 999)  # Market order approximation
                )
                results.append({
                    "position_id": pos.get("id"),
                    "market_slug": market_slug_val,
                    "side": side,
                    "close_result": result,
                })
            except Exception as e:
                results.append({
                    "position_id": pos.get("id"),
                    "market_slug": market_slug_val,
                    "error": str(e),
                })

        # Invalidate position cache since we just changed positions
        _get_cache().invalidate("positions")

        return {
            "success": True,
            "reason": reason,
            "closed_count": len(results),
            "details": results,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def partial_close_position(
    position_id: int | None = None,
    market_slug: str = "",
    close_pct: float = 0.5,
) -> dict[str, Any]:
    """Partially close a position (e.g., cash out 50% for guaranteed profit).

    Args:
        position_id: Specific position ID to partially close
        market_slug: Close this percentage of ALL positions in the market
        close_pct: Percentage to close (0.0-1.0, default 0.5 = 50%)

    Returns:
        dict with partial close result details
    """
    try:
        executor = _get_executor()

        # Get current positions
        portfolio = asyncio.get_event_loop().run_until_complete(executor.get_portfolio())
        positions = portfolio.get("positions", [])

        if position_id is not None:
            target_positions = [p for p in positions if str(p.get("id")) == str(position_id)]
            if not target_positions:
                return {"success": False, "error": f"Position {position_id} not found"}

        elif market_slug:
            target_positions = [p for p in positions if p.get("marketSlug") == market_slug]
            if not target_positions:
                return {"success": False, "error": f"No positions found in market '{market_slug}'"}

        else:
            return {
                "success": False,
                "error": "Either position_id or market_slug must be specified",
            }

        results = []
        for pos in target_positions:
            quantity = pos.get("quantity", 0) * close_pct
            if quantity <= 0:
                results.append({
                    "position_id": pos.get("id"),
                    "error": f"Calculated quantity {quantity} is zero or negative",
                })
                continue

            market_slug_val = pos.get("marketSlug", "")
            side = pos.get("side", "BUY")  # Opposite direction to close

            try:
                result = asyncio.get_event_loop().run_until_complete(
                    executor._place_order(market_slug_val, side.lower(), 1.0, quantity)
                )
                results.append({
                    "position_id": pos.get("id"),
                    "market_slug": market_slug_val,
                    "side": side,
                    "quantity_closed": round(quantity, 4),
                    "close_result": result,
                })
            except Exception as e:
                results.append({
                    "position_id": pos.get("id"),
                    "error": str(e),
                })

        # Invalidate position cache
        _get_cache().invalidate("positions")

        return {
            "success": True,
            "close_pct": close_pct * 100,
            "closed_count": len(results),
            "details": results,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def get_position_history(market_slug: str = "", limit: int = 50) -> dict[str, Any]:
    """Get historical position data (closed positions).

    Args:
        market_slug: Optional filter by market
        limit: Max number of entries to return

    Returns:
        dict with position history
    """
    try:
        executor = _get_executor()
        activities = asyncio.get_event_loop().run_until_complete(executor.get_activities(limit=limit * 2))

        # Filter for position-related activities
        position_history = []
        for activity in activities:
            if activity.get("type") in ("POSITION_OPEN", "POSITION_CLOSE", "RESOLUTION"):
                if not market_slug or activity.get("marketSlug") == market_slug:
                    position_history.append(activity)

        return {
            "success": True,
            "total_entries": len(position_history),
            "history": position_history[:limit],
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }
