"""Bundle Arbitrage Strategy — finds YES+NO mispricings for guaranteed profit.

Uses Polymarket Exchange public gateway + authenticated API.
"""

from loguru import logger


class BundleArbitrageStrategy:
    """Finds bundle arbitrage opportunities on Polymarket Exchange.

    When YES + NO prices don't sum to ~$1.00, buy both sides for guaranteed profit.
    Uses instrument schemas to identify markets programmatically (no slug parsing).
    """

    def __init__(self, config: dict, risk_manager, position_tracker):
        self.config = config
        self.risk_manager = risk_manager
        self.position_tracker = position_tracker
        self.min_edge_pct = config.get("min_edge_pct", 0.02)
        self.max_position_usdc = config.get("max_position_usdc", 30)

    def scan(self) -> list[dict]:
        """Scan all active markets for bundle arbitrage opportunities."""
        from poly_agent.public_client.gateway import PublicGatewayClient

        gateway = PublicGatewayClient(environment=self.risk_manager.config.get("auth", {}).get("environment", "preprod"))

        # Fetch active markets via public gateway (no auth needed)
        markets = gateway.get_markets(limit=300, closed=False)

        opportunities = []

        for market in markets[:200]:  # Scan first 200 active markets per cycle
            try:
                book = gateway.get_order_book(market.get("slug") or market.get("id"))
                if not book:
                    continue

                yes_price = self._best_ask(book, "YES")
                no_price = self._best_ask(book, "NO")

                if yes_price is None or no_price is None:
                    continue

                # Check for bundle arbitrage (buy both sides)
                bundle_sum = yes_price + no_price
                if bundle_sum < 1.0 - self.min_edge_pct:
                    edge = (1.0 - bundle_sum) / bundle_sum * 100
                    size = min(self.max_position_usdc, self.risk_manager.state.remaining_budget_usdc * 0.3)

                    opportunities.append({
                        "strategy_name": "bundle_arbitrage",
                        "description": f"Bundle arb: YES${yes_price:.4f}+NO${no_price:.4f}=${bundle_sum:.4f}",
                        "market_slug": market.get("slug") or market.get("id"),
                        "side": "BUY",
                        "price_yes": yes_price,
                        "price_no": no_price,
                        "size_usdc": round(size, 2),
                        "edge_pct": edge / 100,
                        "confidence": min(0.95, edge * 2),
                        "metadata": {"bundle_sum": bundle_sum},
                    })

                # Check for reverse arb (sell both sides)
                bid_yes = self._best_bid(book, "YES")
                bid_no = self._best_bid(book, "NO")
                if bid_yes and bid_no:
                    sell_sum = bid_yes + bid_no
                    if sell_sum > 1.0 + self.min_edge_pct:
                        edge = (sell_sum - 1.0) / sell_sum * 100
                        size = min(self.max_position_usdc, self.risk_manager.state.remaining_budget_usdc * 0.3)

                        opportunities.append({
                            "strategy_name": "bundle_arbitrage",
                            "description": f"Reverse arb: YES${bid_yes:.4f}+NO${bid_no:.4f}=${sell_sum:.4f}",
                            "market_slug": market.get("slug") or market.get("id"),
                            "side": "SELL",
                            "price_yes": bid_yes,
                            "price_no": bid_no,
                            "size_usdc": round(size, 2),
                            "edge_pct": edge / 100,
                            "confidence": min(0.95, edge * 2),
                            "metadata": {"sell_sum": sell_sum},
                        })

            except Exception as e:
                logger.debug(f"   ⏭️ Skipped market {market.get('slug', '?')}: {e}")

        return opportunities

    def _best_ask(self, book: dict, side: str) -> float | None:
        """Get best ask price for a side."""
        asks = book.get("asks", [])
        if not asks:
            return None
        matching = [a for a in asks if side.lower() in str(a).lower()]
        return float(matching[0].get("price") or 0) if matching else None

    def _best_bid(self, book: dict, side: str) -> float | None:
        """Get best bid price for a side."""
        bids = book.get("bids", [])
        if not bids:
            return None
        matching = [b for b in bids if side.lower() in str(b).lower()]
        return float(matching[0].get("price") or 0) if matching else None
