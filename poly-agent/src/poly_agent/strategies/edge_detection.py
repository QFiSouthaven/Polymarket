"""Edge Detection Strategy — finds mispriced markets vs. external truth sources.

Uses Polymarket Exchange public gateway + instrument schemas for identification.
"""

from loguru import logger


class EdgeDetectionStrategy:
    """Finds markets where Polymarket price differs from 'true' probability.

    Sources of truth (pluggable):
    - News sentiment analysis (AI-powered)
    - Historical event accuracy tracking
    - Polling aggregators (538, RCP)
    - Weather forecasts for outdoor events
    """

    def __init__(self, config: dict, risk_manager, position_tracker):
        self.config = config
        self.risk_manager = risk_manager
        self.position_tracker = position_tracker
        self.min_edge_pct = config.get("min_edge_pct", 0.05)
        self.lookback_hours = config.get("lookback_hours", 24)

    def scan(self) -> list[dict]:
        """Scan markets for edge opportunities."""
        from poly_agent.public_client.gateway import PublicGatewayClient
        from poly_agent.instrument_schema.sports import SportsSchemaParser
        from poly_agent.instrument_schema.crypto import CryptoSchemaParser

        gateway = PublicGatewayClient(environment=self.risk_manager.config.get("auth", {}).get("environment", "preprod"))

        markets = gateway.get_markets(limit=300, closed=False)
        opportunities = []

        for market in markets[:250]:  # Scan more markets (lower edge threshold)
            try:
                price = self._get_market_price(gateway, market)
                if not price or price <= 0:
                    continue

                # Identify market type via instrument schema (no slug parsing!)
                parsed_sports = SportsSchemaParser.parse(market)
                parsed_crypto = CryptoSchemaParser.parse(market)

                true_prob = None
                source_name = "unknown"

                if parsed_sports and SportsSchemaParser.is_interesting(parsed_sports):
                    # Sports markets: use historical accuracy + news sentiment
                    true_prob = self._sports_edge_estimate(parsed_sports, market)
                    source_name = f"sports_{parsed_sports['type'].lower()}"

                elif parsed_crypto and CryptoSchemaParser.is_interesting(parsed_crypto):
                    # Crypto price markets: compare to reference index (BRTI for BTC)
                    true_prob = self._crypto_edge_estimate(parsed_crypto, market)
                    source_name = f"crypto_{parsed_crypto['family']}"

                if true_prob is None or abs(true_prob - price) < self.min_edge_pct:
                    continue

                edge = abs(true_prob - price)
                direction = "BUY" if true_prob > price else "SELL"
                confidence = min(0.9, edge * 3)
                size_usdc = self._calculate_size(edge, price)

                opportunities.append({
                    "strategy_name": "edge_detection",
                    "description": f"{market.get('title', '?')}: PM={price:.4f} vs True≈{true_prob:.4f}",
                    "market_slug": market.get("slug") or market.get("id"),
                    "side": direction,
                    "price": price,
                    "size_usdc": size_usdc,
                    "edge_pct": edge,
                    "confidence": confidence,
                    "metadata": {
                        "true_prob_estimate": true_prob,
                        "market_price": price,
                        "source": source_name,
                        "parsed_type": parsed_sports or parsed_crypto,
                    },
                })

            except Exception as e:
                logger.debug(f"   ⏭️ Edge scan failed for {market.get('slug', '?')}: {e}")

        return opportunities

    def _get_market_price(self, gateway, market: dict) -> float | None:
        """Get current YES token price."""
        slug = market.get("slug") or market.get("id")
        detail = gateway.get_market_detail(slug)
        if detail:
            return float(detail.get("price") or 0)
        # Fallback to BBO
        bbo = gateway.get_bbo(slug)
        if bbo and bbo.get("bestBid"):
            return float(bbo["bestBid"])
        return None

    def _sports_edge_estimate(self, parsed: dict, market: dict) -> float | None:
        """Estimate true probability for sports markets.

        In production: combine historical accuracy data + news sentiment analysis.
        For now, returns None (requires external data sources configured).
        """
        # Placeholder — would call AI model to analyze recent game data, injuries, etc.
        return None

    def _crypto_edge_estimate(self, parsed: dict, market: dict) -> float | None:
        """Estimate true probability for crypto price markets.

        Compares Polymarket price against the reference index (BRTI for BTC).
        For updown markets: if current BRTI > open price → BUY YES (upside likely)
        For strike markets: compare strike to current index level
        """
        # In production: fetch real-time BRTI from CF Benchmarks API
        # For now, returns None (requires external data source configured)
        return None

    def _calculate_size(self, edge: float, price: float) -> float:
        """Calculate optimal bet size based on Kelly criterion (simplified)."""
        max_per_trade = self.risk_manager.config["capital"]["max_per_trade_usdc"]
        size = min(max_per_trade * 0.5, max_per_trade * edge * 10)
        return round(max(5, size), 2)
