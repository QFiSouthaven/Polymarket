"""Market Scan tools — scan, search, and retrieve Polymarket market data.

Uses the existing PublicGatewayClient from poly-agent/src/poly_agent/public_client/gateway.py
for unauthenticated public API access, with caching via PolymarketCache.

Provides:
- scan_markets: browse active markets with filters (category, volume)
- get_market_detail: detailed info for a specific market by slug
- search_markets: keyword search across events and markets
"""

import asyncio
from typing import Any


def _get_gateway_client() -> "PublicGatewayClient":
    """Get the public gateway client from poly-agent."""
    import sys
    # Add poly-agent src to path if not already there
    workspace_root = __file__.resolve().parent.parent.parent.parent
    agent_src = workspace_root / "poly-agent" / "src"
    if str(agent_src) not in sys.path:
        sys.path.insert(0, str(agent_src))

    from poly_agent.public_client.gateway import PublicGatewayClient
    return PublicGatewayClient(environment="prod")


def _get_cache() -> Any:
    """Get the polymarket cache singleton."""
    from ..persistence.polymarket_cache import get_polymarket_cache
    return get_polymarket_cache()


def scan_markets(
    limit: int = 50,
    category: str = "",
    min_volume_24h: float = 0,
    closed: bool = False,
) -> dict[str, Any]:
    """Scan Polymarket for active markets.

    Args:
        limit: Max number of markets to return (default 50)
        category: Filter by category (e.g., 'politics', 'sports', 'crypto')
        min_volume_24h: Minimum 24h volume threshold in USDC
        closed: If True, include closed/resolved markets

    Returns:
        dict with list of markets and metadata
    """
    try:
        client = _get_gateway_client()
        markets = client.get_markets(limit=limit * 5, closed=closed)

        # Apply filters
        filtered = []
        for m in markets:
            # Filter by category (check tags/title)
            if category:
                cat_lower = category.lower()
                title = str(m.get("title", "")).lower()
                tags = [t.get("slug", "").lower() for t in m.get("tags", [])]
                if not any(cat_lower in tag or cat_lower in title for tag in tags):
                    continue

            # Filter by volume
            vol_24h = m.get("volume24h", 0) or m.get("volume_24h", 0) or 0
            if min_volume_24h > 0 and vol_24h < min_volume_24h:
                continue

            filtered.append(m)

        # Sort by volume descending
        filtered.sort(key=lambda x: (x.get("volume24h", 0) or x.get("volume_24h", 0) or 0), reverse=True)

        # Cache the result
        cache_key = f"scan_markets:{limit}:{category}:{min_volume_24h}"
        _get_cache().set(cache_key, filtered, ttl_seconds=300)

        return {
            "success": True,
            "total_available": len(markets),
            "filtered_count": len(filtered),
            "markets": [
                {
                    "slug": m.get("slug", ""),
                    "title": m.get("title", ""),
                    "category": m.get("category", ""),
                    "volume_24h": m.get("volume24h", 0) or m.get("volume_24h", 0),
                    "price_yes": m.get("price", 0),
                    "price_no": m.get("priceNo", m.get("price_no", 1 - (m.get("price", 0) or 0))),
                    "open_interest": m.get("openInterest", m.get("open_interest", 0)),
                    "closed": m.get("closed", False),
                }
                for m in filtered[:limit]
            ],
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "markets": [],
        }


def get_market_detail(market_slug: str) -> dict[str, Any]:
    """Get detailed information about a specific Polymarket market.

    Args:
        market_slug: The unique slug identifier for the market (e.g., 'will-trump-win-2024')

    Returns:
        dict with full market details including order book, price history, and metadata
    """
    try:
        client = _get_gateway_client()

        # Check cache first
        cached = _get_cache().get_cached_market(market_slug)
        if cached:
            return {"success": True, "source": "cache", "market": cached}

        # Get market detail
        market = client.get_market_detail(market_slug)
        if not market:
            return {
                "success": False,
                "error": f"Market '{market_slug}' not found or API error",
            }

        # Get order book
        order_book = client.get_order_book(market_slug)

        # Get BBO (best bid/offer)
        bbo = client.get_bbo(market_slug)

        result = {
            "success": True,
            "source": "live",
            "market": market,
            "order_book": order_book or {},
            "bbo": bbo or {},
        }

        # Cache the result
        _get_cache().set_cached_market(market_slug, result)

        return result

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def search_markets(query: str, limit: int = 20) -> dict[str, Any]:
    """Search Polymarket markets and events by keyword.

    Args:
        query: Search keywords (e.g., 'Trump', 'NBA Finals')
        limit: Max results to return

    Returns:
        dict with search results across events and markets
    """
    try:
        client = _get_gateway_client()

        # Use the public gateway's search if available, otherwise filter locally
        # The PublicGatewayClient doesn't have a direct search method, so we fetch
        # events/markets and filter by query in the title/tags
        markets = client.get_markets(limit=500)
        events = client.get_events(limit=200)

        results = []

        # Search in markets
        for m in markets:
            title = str(m.get("title", "")).lower()
            tags = " ".join(t.get("slug", "").lower() for t in m.get("tags", [])).lower()
            if query.lower() in title or query.lower() in tags:
                results.append({
                    "type": "market",
                    "id": m.get("slug", ""),
                    "title": m.get("title", ""),
                    "category": m.get("category", ""),
                    "volume_24h": m.get("volume24h", 0) or m.get("volume_24h", 0),
                })

        # Search in events
        for e in events:
            title = str(e.get("title", "")).lower()
            if query.lower() in title:
                results.append({
                    "type": "event",
                    "id": e.get("slug", ""),
                    "title": e.get("title", ""),
                    "category": e.get("category", ""),
                    "market_count": len(e.get("markets", [])),
                })

        # Sort by relevance (markets first, then by volume)
        results.sort(key=lambda x: (0 if x["type"] == "market" else 1, -(x.get("volume_24h", 0))))

        return {
            "success": True,
            "query": query,
            "total_results": len(results),
            "results": results[:limit],
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def get_market_price(market_slug: str) -> dict[str, Any]:
    """Get the current price (probability) for a market.

    Args:
        market_slug: The unique slug identifier for the market

    Returns:
        dict with YES/NO prices and confidence interval
    """
    try:
        client = _get_gateway_client()

        # Check cache first
        cached_price = _get_cache().get_cached_price(market_slug)
        if cached_price is not None:
            return {"success": True, "source": "cache", "market_slug": market_slug, "price_yes": cached_price}

        # Get BBO for current price
        bbo = client.get_bbo(market_slug)
        if not bbo:
            return {
                "success": False,
                "error": f"Could not get price for '{market_slug}'",
            }

        price_yes = bbo.get("bestBid", 0) or bbo.get("bid", 0)
        price_no = bbo.get("bestAsk", 0) or bbo.get("ask", 0)

        # Cache the result
        _get_cache().set_cached_price(market_slug, price_yes)

        return {
            "success": True,
            "source": "live",
            "market_slug": market_slug,
            "price_yes": round(price_yes, 4),
            "price_no": round(1 - price_yes, 4),
            "bid": bbo.get("bestBid", 0),
            "ask": bbo.get("bestAsk", 0),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def get_events(category: str = "", limit: int = 50) -> dict[str, Any]:
    """Get Polymarket events (groups of related markets).

    Args:
        category: Filter by category
        limit: Max number of events to return

    Returns:
        dict with list of events and metadata
    """
    try:
        client = _get_gateway_client()

        # Check cache
        cached = _get_cache().get_cached_events()
        if cached:
            filtered = [e for e in cached if not category or category.lower() in str(e.get("category", "")).lower()]
            return {"success": True, "source": "cache", "events": filtered[:limit]}

        events = client.get_events(limit=limit * 5)

        # Filter by category if specified
        if category:
            cat_lower = category.lower()
            events = [e for e in events if cat_lower in str(e.get("category", "")).lower()]

        # Cache the result
        _get_cache().set_cached_events(events)

        return {
            "success": True,
            "total_available": len(events),
            "events": [
                {
                    "slug": e.get("slug", ""),
                    "title": e.get("title", ""),
                    "category": e.get("category", ""),
                    "market_count": len(e.get("markets", [])),
                    "closed": e.get("closed", False),
                }
                for e in events[:limit]
            ],
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def get_series() -> dict[str, Any]:
    """Get all Polymarket series (e.g., NFL 2025-26 Season)."""
    try:
        client = _get_gateway_client()
        series = client.get_series()

        return {
            "success": True,
            "series_count": len(series),
            "series": [
                {"id": s.get("id", ""), "name": s.get("name", ""), "slug": s.get("slug", "")}
                for s in series[:100]
            ],
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def get_sports() -> dict[str, Any]:
    """Get Polymarket sports leagues and teams data."""
    try:
        client = _get_gateway_client()
        sports_data = client.get_sports()

        return {
            "success": True,
            "sports_count": len(sports_data) if isinstance(sports_data, dict) else 0,
            "data": sports_data,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }
