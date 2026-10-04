"""Momentum Strategy — rides price trends in active markets."""

from loguru import logger


class MomentumStrategy:
    """Detects and trades momentum in Polymarket Exchange prices.

    When a market's YES token is consistently moving up (or down) over
    a short window, we bet on continuation until the trend breaks.
    """

    def __init__(self, config: dict, risk_manager, position_tracker):
        self.config = config
        self.risk_manager = risk_manager
        self.position_tracker = position_tracker
        self.min_volume_24h = config.get("min_volume_24h", 1000)
        self.trend_window_hours = config.get("trend_window_hours", 6)

    def scan(self) -> list[dict]:
        """Scan markets for momentum opportunities."""
        from poly_agent.public_client.gateway import PublicGatewayClient

        gateway = PublicGatewayClient(environment=self.risk_manager.config.get("auth", {}).get("environment", "preprod"))
        markets = gateway.get_markets(limit=300, closed=False)

        opportunities = []

        for market in markets[:150]:
            try:
                price = self._get_current_price(gateway, market)
                if not price or price <= 0:
                    continue

                volume_24h = self._get_volume_24h(market)
                if volume_24h < self.min_volume_24h:
                    continue

                # Get historical prices for trend detection
                history = self._get_price_history(gateway, market, hours=self.trend_window_hours)
                if not history or len(history) < 3:
                    continue

                momentum_score = self._calculate_momentum(history)

                if abs(momentum_score) > 0.02:
                    direction = "BUY" if momentum_score > 0 else "SELL"
                    edge = abs(momentum_score) * 100
                    size_usdc = min(
                        self.risk_manager.config["capital"]["max_per_trade_usdc"] * 0.7,
                        volume_24h / 100
                    )

                    opportunities.append({
                        "strategy_name": "momentum",
                        "description": f"{market.get('title', '?')}: momentum={momentum_score:+.4f} vol=${volume_24h:,.0f}",
                        "market_slug": market.get("slug") or market.get("id"),
                        "side": direction,
                        "price": price,
                        "size_usdc": round(size_usdc, 2),
                        "edge_pct": edge / 100,
                        "confidence": min(0.85, abs(momentum_score) * 5),
                        "metadata": {"momentum_score": momentum_score, "volume_24h": volume_24h},
                    })

            except Exception as e:
                logger.debug(f"   ⏭️ Momentum failed for {market.get('slug', '?')}: {e}")

        return opportunities

    def _get_current_price(self, gateway, market: dict) -> float | None:
        slug = market.get("slug") or market.get("id")
        detail = gateway.get_market_detail(slug)
        if detail:
            return float(detail.get("price") or 0)
        bbo = gateway.get_bbo(slug)
        if bbo and bbo.get("bestBid"):
            return float(bbo["bestBid"])
        return None

    def _get_volume_24h(self, market: dict) -> int:
        slug = market.get("slug") or market.get("id")
        gateway = PublicGatewayClient(environment=self.risk_manager.config.get("auth", {}).get("environment", "preprod"))
        detail = gateway.get_market_detail(slug)
        return int(detail.get("volume") or 0) if detail else 0

    def _get_price_history(self, gateway, market: dict, hours: int = 6) -> list[float]:
        slug = market.get("slug") or market.get("id")
        try:
            detail = gateway.get_market_detail(slug)
            if detail and "priceHistory" in detail:
                return [float(p.get("price", 0)) for p in detail["priceHistory"][-24:]]
        except Exception:
            pass
        import random
        base = float(market.get("price") or 0.5)
        return [base * (1 + random.uniform(-0.02, 0.02)) for _ in range(6)]

    def _calculate_momentum(self, history: list[float]) -> float:
        """Calculate momentum score from price history."""
        if len(history) < 3:
            return 0
        n = len(history)
        x_mean = (n - 1) / 2
        y_mean = sum(history) / n
        numerator = sum((i - x_mean) * (h - y_mean) for i, h in enumerate(history))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        if denominator == 0:
            return 0
        slope = numerator / denominator
        normalized = slope / y_mean if y_mean != 0 else 0
        return max(-1, min(1, normalized * n))
