"""Order Tools — create, cancel, modify, and preview orders on Polymarket.

Uses the existing PolymarketExecutor from poly-agent/src/poly_agent/execution/executor.py
for authenticated order operations.

Provides:
- create_order: place a new limit/market order
- cancel_order: cancel a specific open order
- cancel_all_orders: cancel all orders (optionally filtered by market)
- preview_order: validate parameters and see expected fills before submission
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


def create_order(
    market_slug: str,
    side: str,
    price: float,
    size_usdc: float,
    order_type: str = "LIMIT",
) -> dict[str, Any]:
    """Create a new order on Polymarket.

    Args:
        market_slug: The unique slug identifier for the market
        side: 'BUY' or 'SELL' (direction of the position)
        price: Limit price (e.g., 0.65 means you want to buy at 65¢)
        size_usdc: Size in USDC (e.g., 25 = $25 worth)
        order_type: Order type — 'LIMIT' or 'MARKET'

    Returns:
        dict with order result including order_id and status
    """
    try:
        executor = _get_executor()

        # Validate inputs
        if side.upper() not in ("BUY", "SELL"):
            return {"success": False, "error": f"Invalid side '{side}'. Must be BUY or SELL"}

        if price <= 0 or price > 1:
            return {"success": False, "error": f"Price must be between 0 and 1 (got {price})"}

        if size_usdc <= 0:
            return {"success": False, "error": f"Size must be positive (got {size_usdc})"}

        # Calculate quantity from USDC amount and price
        quantity = size_usdc / price if price > 0 else 0

        # Build order body per Polymarket Exchange API spec
        body = {
            "marketSlug": market_slug,
            "intent": f"ORDER_INTENT_{side.upper()}_LONG",
            "type": f"ORDER_TYPE_{order_type}",
            "price": {"value": str(round(price, 4)), "currency": "USD"},
            "quantity": quantity,
        }

        # Execute the order
        result = asyncio.get_event_loop().run_until_complete(
            executor._place_order(market_slug, side.lower(), price, size_usdc)
        )

        return {
            "success": True,
            "order_id": result.get("order_id", ""),
            "market_slug": market_slug,
            "side": side.upper(),
            "price": round(price, 4),
            "quantity": round(quantity, 4),
            "size_usdc": size_usdc,
            "status": "placed" if result.get("success") else "failed",
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def cancel_order(order_id: str) -> dict[str, Any]:
    """Cancel a specific open order by its exchange-assigned ID.

    Args:
        order_id: The order ID returned from create_order or get_open_orders

    Returns:
        dict with cancellation result
    """
    try:
        executor = _get_executor()

        success = asyncio.get_event_loop().run_until_complete(
            executor.cancel_order(order_id)
        )

        return {
            "success": True,
            "order_id": order_id,
            "cancelled": success,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def cancel_all_orders(market_slug: str = "") -> dict[str, Any]:
    """Cancel all open orders. Optionally filter by market slug.

    Args:
        market_slug: If provided, only cancel orders in this market

    Returns:
        dict with cancellation summary
    """
    try:
        executor = _get_executor()

        # Get current open orders
        open_orders = asyncio.get_event_loop().run_until_complete(
            executor.get_open_orders()
        )

        if not open_orders:
            return {
                "success": True,
                "cancelled_count": 0,
                "message": "No open orders to cancel",
            }

        # Filter by market slug if specified
        if market_slug:
            open_orders = [o for o in open_orders if o.get("marketSlug") == market_slug]

        cancelled_ids = []
        failed_ids = []

        for order in open_orders:
            oid = order.get("id", "") or order.get("orderId", "")
            if not oid:
                continue

            success = asyncio.get_event_loop().run_until_complete(
                executor.cancel_order(oid)
            )
            if success:
                cancelled_ids.append(oid)
            else:
                failed_ids.append(oid)

        return {
            "success": True,
            "cancelled_count": len(cancelled_ids),
            "failed_count": len(failed_ids),
            "cancelled_order_ids": cancelled_ids,
            "failed_order_ids": failed_ids,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def preview_order(
    market_slug: str,
    side: str,
    price: float,
    size_usdc: float,
) -> dict[str, Any]:
    """Preview an order before submission to validate parameters and see expected fills.

    This checks:
    - Order book depth at the requested price level
    - Expected fill quantity (how many contracts you'd get)
    - Price impact (slippage estimate)
    - Risk limit compliance

    Args:
        market_slug: The unique slug identifier for the market
        side: 'BUY' or 'SELL'
        price: Requested limit price
        size_usdc: Size in USDC

    Returns:
        dict with preview details including expected fills and risk check results
    """
    try:
        executor = _get_executor()

        # Get order book for this market
        order_book = asyncio.get_event_loop().run_until_complete(
            executor._place_order.__self__.token_mgr.get_headers("GET")  # Get auth headers
        )

        # Use the public gateway client for order book (no auth needed)
        import sys
        workspace_root = __file__.resolve().parent.parent.parent.parent
        agent_src = workspace_root / "poly-agent" / "src"
        if str(agent_src) not in sys.path:
            sys.path.insert(0, str(agent_src))

        from poly_agent.public_client.gateway import PublicGatewayClient
        gateway = PublicGatewayClient(environment="prod")
        ob = gateway.get_order_book(market_slug) or {}

        # Get BBO for current price reference
        bbo = gateway.get_bbo(market_slug) or {}

        # Calculate expected fills from order book
        bids = ob.get("bids", [])  # [(price, quantity), ...] sorted desc by price
        asks = ob.get("asks", [])  # [(price, quantity), ...] sorted asc by price

        if side.upper() == "BUY":
            # For BUY: match against asks (you want to buy at or below your limit)
            fill_price = bbo.get("bestAsk", price)
            fill_quantity = min(size_usdc / price, 1000)  # Cap at reasonable quantity

            # Calculate expected cost from order book depth
            remaining_size = size_usdc
            total_cost = 0
            filled_from_book = []
            for ask_price, ask_qty in asks:
                if remaining_size <= 0:
                    break
                qty_to_fill = min(ask_qty, remaining_size / ask_price)
                cost = qty_to_fill * ask_price
                total_cost += cost
                remaining_size -= cost
                filled_from_book.append({"price": ask_price, "quantity": round(qty_to_fill, 4)})

            expected_slippage = abs(price - fill_price) if price > 0 else 0

        else:
            # For SELL: match against bids (you want to sell at or above your limit)
            fill_price = bbo.get("bestBid", price)
            fill_quantity = min(size_usdc / price, 1000)

            remaining_size = size_usdc
            total_cost = 0
            filled_from_book = []
            for bid_price, bid_qty in bids:
                if remaining_size <= 0:
                    break
                qty_to_fill = min(bid_qty, remaining_size / bid_price)
                cost = qty_to_fill * bid_price
                total_cost += cost
                remaining_size -= cost
                filled_from_book.append({"price": bid_price, "quantity": round(qty_to_fill, 4)})

            expected_slippage = abs(price - fill_price) if price > 0 else 0

        # Risk check (reuse risk dashboard logic)
        from .risk_dashboard import check_can_trade
        risk_check = check_can_trade(size_usdc)

        return {
            "success": True,
            "preview": {
                "market_slug": market_slug,
                "side": side.upper(),
                "requested_price": round(price, 4),
                "size_usdc": size_usdc,
                "estimated_fill_quantity": round(fill_quantity, 4),
                "expected_fill_price": round(fill_price, 4),
                "expected_slippage_pct": round(expected_slippage * 100, 2),
                "order_book_depth": {
                    "best_bid": bbo.get("bestBid", 0),
                    "best_ask": bbo.get("bestAsk", 0),
                    "spread": round((bbo.get("bestAsk", 0) or 1) - (bbo.get("bestBid", 0) or 0), 4),
                },
                "filled_from_book": filled_from_book[:5],  # Top 5 levels
            },
            "risk_check": risk_check,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def get_open_orders() -> dict[str, Any]:
    """Get all currently open orders.

    Returns:
        dict with list of open orders and summary
    """
    try:
        executor = _get_executor()
        open_orders = asyncio.get_event_loop().run_until_complete(
            executor.get_open_orders()
        )

        return {
            "success": True,
            "count": len(open_orders),
            "orders": open_orders,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def modify_order(
    order_id: str,
    new_price: float | None = None,
    new_quantity: float | None = None,
) -> dict[str, Any]:
    """Modify an existing order (change price and/or quantity).

    Args:
        order_id: The exchange-assigned order ID
        new_price: New limit price (optional)
        new_quantity: New quantity (optional)

    Returns:
        dict with modification result
    """
    try:
        executor = _get_executor()

        # Get current order details first
        open_orders = asyncio.get_event_loop().run_until_complete(
            executor.get_open_orders()
        )
        target_order = None
        for o in open_orders:
            if str(o.get("id")) == str(order_id) or str(o.get("orderId")) == str(order_id):
                target_order = o
                break

        if not target_order:
            return {"success": False, "error": f"Order {order_id} not found in open orders"}

        # Build modification body (cancel-replace pattern)
        current_price = float(target_order.get("price", {}).get("value", 0))
        current_quantity = target_order.get("quantity", 0)

        final_price = new_price if new_price is not None else current_price
        final_quantity = new_quantity if new_quantity is not None else current_quantity

        # Execute cancel-replace via the exchange API
        body = {
            "orderId": order_id,
            "price": {"value": str(round(final_price, 4)), "currency": "USD"},
            "quantity": final_quantity,
        }

        # Use the modify endpoint (POST /v1/orders/{id}/modify)
        import requests
        auth_config = _get_executor().auth_config
        env = auth_config.get("environment", "prod")
        base_url = f"https://api.{env}.polymarketexchange.com" if env == "preprod" else "https://api.polymarket.us"

        token_mgr = executor.token_mgr
        headers = token_mgr.get_headers("POST")
        headers["Content-Type"] = "application/json"

        response = requests.post(
            f"{base_url}/v1/orders/{order_id}/modify",
            headers=headers,
            json=body,
            timeout=10,
        )

        if response.status_code in (200, 204):
            return {
                "success": True,
                "order_id": order_id,
                "modified_price": round(final_price, 4),
                "modified_quantity": final_quantity,
            }
        else:
            return {
                "success": False,
                "error": f"Modify failed ({response.status_code}): {response.text}",
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }
