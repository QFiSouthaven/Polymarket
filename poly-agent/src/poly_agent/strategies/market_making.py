"""Market Making Strategy — captures spreads by placing competitive bid/ask orders."""

from loguru import logger


class MarketMakingStrategy:
    """Places simultaneous buy and sell orders to capture the spread.

    Works on high-liquidity markets where you can profit from the bid-ask spread.
    Lower risk than directional strategies but requires more capital deployed.
    """

    def __init__(self, config: dict, risk_manager, position_tracker):
        self.config = config
        self.risk_manager = risk_manager
        self.position_tracker = position_tracker
        self.min_spread_pct = config.get("min_spread_pct", 0.03)
        self.order_size_usdc = config.get("order_size_usdc", 10)
        self.max_active_orders = config.get("max_active_orders", 50)

    def scan(self) -> list[dict]:
        """Scan for market-making opportunities."""
        from poly_agent.public_client.gateway import PublicGatewayClient

        gateway = PublicGatewayClient(environment=self.risk_manager.config.get("auth", {}).get("environment", "preprod"))
        markets = gateway.get_markets(limit=300, closed=False)

        opportunities = []

        for market in markets[:100]:  # Focus on liquid markets
            try:
                book = gateway.get_order_book(market.get("slug") or market.get("id"))
                if not book:
                    continue

                best_bid = self._best_bid(book, "YES")
                best_ask = self._best_ask(book, "YES")

                if not best_bid or not best_ask or best_ask <= best_bid:
                    continue

                spread_pct = (best_ask - best_bid) / best_bid * 100
                mid_price = (best_bid + best_ask) / 2

                # Only trade if spread is wide enough to profit after fees
                if spread_pct < self.min_spread_pct * 100:
                    continue

                buy_price = round(best_bid + (best_ask - best_bid) * 0.3, 4)
                sell_price = round(best_ask - (best_ask - best_bid) * 0.3, 4)

                opportunities.append({
                    "strategy_name": "market_making",
                    "description": f"MM: {market.get('title', '?')} spread={spread_pct:.2f}% mid=${mid_price:.4f}",
                    "market_slug": market.get("slug") or market.get("id"),
                    "side": "BUY",
                    "price": buy_price,
                    "size_usdc": self.order_size_usdc,
                    "edge_pct": spread_pct / 100 * 0.6,
                    "confidence": min(0.9, spread_pct / 5),
                    "metadata": {"best_bid": best_bid, "best_ask": best_ask, "spread_pct": spread_pct},
                })

            except Exception as e:
                logger.debug(f"   ⏭️ MM failed for {market.get('slug', '?')}: {e}")

        return opportunities[:self.max_active_orders]

    def _best_bid(self, book: dict, side: str) -> float | None:
        bids = book.get("bids", [])
        if not bids:
            return None
        matching = [b for b in bids if side.lower() in str(b).lower()]
        return float(matching[0].get("price") or 0) if matching else None

    def _best_ask(self, book: dict, side: str) -> float | None:
        asks = book.get("asks", [])
        if not asks:
            return None
        matching = [a for a in asks if side.lower() in str(a).lower()]
        return float(matching[0].get("price") or 0) if matching else None
