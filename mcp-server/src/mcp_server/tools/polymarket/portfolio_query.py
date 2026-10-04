"""Portfolio Query tools — get portfolio summary, account balances, and trading activity.

Uses the existing PolymarketExecutor from poly-agent/src/poly_agent/execution/executor.py
for authenticated portfolio queries.

Provides:
- get_portfolio_summary: full portfolio overview (positions + balances)
- get_account_balances: current balance and buying power
- get_activities: recent trading history
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

    import yaml
    config_path = workspace_root / "poly-agent" / "config.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    from poly_agent.execution.executor import PolymarketExecutor
    return PolymarketExecutor(auth_config=config.get("auth", {}))


def get_portfolio_summary() -> dict[str, Any]:
    """Get current portfolio summary including positions and balances.

    Returns:
        dict with full portfolio overview (positions, balances, buying power)
    """
    try:
        executor = _get_executor()

        # Get portfolio data
        portfolio = asyncio.get_event_loop().run_until_complete(executor.get_portfolio())

        positions = portfolio.get("positions", [])
        current_balance = portfolio.get("current_balance", 0) or 0
        buying_power = portfolio.get("buying_power", 0) or 0
        open_orders_value = portfolio.get("open_orders_value", 0) or 0

        # Calculate position-level metrics
        total_unrealized_pnl = sum(
            p.get("unrealizedPnl", 0) or p.get("unrealized_pnl", 0) for p in positions
        )
        total_realized_pnl = sum(
            p.get("realizedPnl", 0) or p.get("realized_pnl", 0) for p in positions
        )

        # Group by market category
        by_category: dict[str, list] = {}
        for pos in positions:
            cat = pos.get("category", "uncategorized")
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(pos)

        # Calculate PnL per category
        pnl_by_category = {}
        for cat, pos_list in by_category.items():
            pnl_by_category[cat] = sum(
                p.get("unrealizedPnl", 0) or p.get("unrealized_pnl", 0) for p in pos_list
            )

        return {
            "success": True,
            "portfolio": {
                "current_balance_usdc": round(current_balance, 2),
                "buying_power_usdc": round(buying_power, 2),
                "open_orders_value_usdc": round(open_orders_value, 2),
                "total_positions": len(positions),
                "unrealized_pnl_usdc": round(total_unrealized_pnl, 2),
                "realized_pnl_usdc": round(total_realized_pnl, 2),
                "net_portfolio_value_usdc": round(current_balance + total_unrealized_pnl, 2),
            },
            "positions_by_category": {
                cat: {
                    "count": len(pos_list),
                    "unrealized_pnl_usdc": round(pnl_by_category[cat], 2),
                    "positions": [
                        {
                            "market_slug": p.get("slug", ""),
                            "side": p.get("side", ""),
                            "quantity": p.get("quantity", 0),
                            "entry_price": p.get("entryPrice", p.get("entry_price", 0)),
                            "current_price": p.get("currentPrice", p.get("current_price", 0)),
                            "unrealized_pnl_usdc": round(
                                (p.get("unrealizedPnl", 0) or p.get("unrealized_pnl", 0)), 2
                            ),
                        }
                        for p in pos_list[:10]  # Top 10 per category
                    ],
                }
                for cat, pos_list in by_category.items()
            },
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def get_account_balances() -> dict[str, Any]:
    """Get account balances including current balance and buying power.

    Returns:
        dict with detailed balance information
    """
    try:
        executor = _get_executor()

        # Get account balances via the API
        headers = executor.token_mgr.get_headers("GET")
        env = executor.env
        base_url = f"https://api.{env}.polymarketexchange.com" if env == "preprod" else "https://api.polymarket.us"

        response = asyncio.get_event_loop().run_until_complete(
            _async_get(f"{base_url}/v1/account/balances", headers, timeout=5)
        )

        if response and response.status_code == 200:
            data = response.json()
            balances = data.get("balances", [{}])[0] if isinstance(data.get("balances"), list) else {}

            return {
                "success": True,
                "balances": {
                    "current_balance_usdc": round(balances.get("currentBalance", 0), 2),
                    "buying_power_usdc": round(balances.get("buyingPower", 0), 2),
                    "open_orders_value_usdc": round(balances.get("openOrders", 0), 2),
                    "available_for_trading_usdc": round(
                        balances.get("currentBalance", 0) - balances.get("openOrders", 0), 2
                    ),
                },
            }

        return {
            "success": False,
            "error": f"API returned status {response.status_code if response else 'timeout'}",
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def get_activities(limit: int = 50) -> dict[str, Any]:
    """Get recent trading activity (trades, position resolutions, balance changes).

    Args:
        limit: Max number of activities to return (default 50)

    Returns:
        dict with list of recent activities and summary
    """
    try:
        executor = _get_executor()

        # Get activities via the API
        headers = executor.token_mgr.get_headers("GET")
        env = executor.env
        base_url = f"https://api.{env}.polymarketexchange.com" if env == "preprod" else "https://api.polymarket.us"

        response = asyncio.get_event_loop().run_until_complete(
            _async_get(
                f"{base_url}/v1/portfolio/activities?limit={limit}&sortOrder=SORT_ORDER_DESCENDING",
                headers,
                timeout=5,
            )
        )

        if response and response.status_code == 200:
            data = response.json()
            activities = data.get("activities", [])

            # Categorize activities
            trade_count = sum(1 for a in activities if "ORDER_FILLED" in str(a.get("type", "")))
            resolution_count = sum(1 for a in activities if "RESOLUTION" in str(a.get("type", "")))
            balance_change_count = sum(1 for a in activities if "BALANCE_CHANGE" in str(a.get("type", "")))

            return {
                "success": True,
                "total_activities": len(activities),
                "summary": {
                    "trades": trade_count,
                    "resolutions": resolution_count,
                    "balance_changes": balance_change_count,
                },
                "activities": [
                    {
                        "id": a.get("id", ""),
                        "type": a.get("type", ""),
                        "market_slug": a.get("marketSlug", ""),
                        "timestamp": a.get("createdAt", a.get("created_at", "")),
                        "amount_usdc": round(a.get("amount", 0) or a.get("amountUsdc", 0), 2),
                        "description": a.get("description", ""),
                    }
                    for a in activities[:limit]
                ],
            }

        return {
            "success": False,
            "error": f"API returned status {response.status_code if response else 'timeout'}",
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def get_position_ledger(limit: int = 100) -> dict[str, Any]:
    """Get the full position ledger (historical changes for all positions).

    Args:
        limit: Max entries to return

    Returns:
        dict with position ledger history
    """
    try:
        executor = _get_executor()

        headers = executor.token_mgr.get_headers("GET")
        env = executor.env
        base_url = f"https://api.{env}.polymarketexchange.com" if env == "preprod" else "https://api.polymarket.us"

        response = asyncio.get_event_loop().run_until_complete(
            _async_get(f"{base_url}/v1/positions/ledger?limit={limit}", headers, timeout=5)
        )

        if response and response.status_code == 200:
            data = response.json()
            ledger_entries = data.get("entries", [])

            return {
                "success": True,
                "total_entries": len(ledger_entries),
                "entries": [
                    {
                        "id": e.get("id", ""),
                        "market_slug": e.get("marketSlug", ""),
                        "type": e.get("type", ""),  # OPEN, CLOSE, RESOLUTION
                        "quantity_change": e.get("quantityChange", 0),
                        "price": e.get("price", 0),
                        "timestamp": e.get("createdAt", ""),
                    }
                    for e in ledger_entries[:limit]
                ],
            }

        return {
            "success": False,
            "error": f"API returned status {response.status_code if response else 'timeout'}",
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


# --- Async HTTP helper ---

async def _async_get(url: str, headers: dict, timeout: int = 5) -> Any:
    """Async GET request using asyncio and aiohttp-like pattern."""
    import asyncio

    # Use requests in executor for simplicity (matches existing poly-agent pattern)
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, lambda: _sync_get(url, headers, timeout)
    )


def _sync_get(url: str, headers: dict, timeout: int = 5):
    """Synchronous GET request."""
    import requests
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        return response
    except Exception as e:
        print(f"GET {url} failed: {e}")
        return None
