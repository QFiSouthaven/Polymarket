"""Crypto instrument schema parser — identifies crypto price markets from metadata.

Per Polymarket Exchange docs: "Map on `crypto_market_type`."
Never parse the symbol or slug to determine market type.
"""


class CryptoSchemaParser:
    """Parses crypto instrument metadata to identify market family and structure."""

    # Market families mapped to descriptions
    MARKET_FAMILIES = {
        "strike": ("Above/Below Strike", "Ladder of independent binary instruments"),
        "range": ("Price Range Bucket", "Mutually exclusive buckets tiling the price line"),
        "hit": ("One-Touch Target", "Independent binaries per target level"),
    }

    # Horizons mapped to descriptions
    HORIZONS = {
        "5m": "5-minute window",
        "15m": "15-minute window",
        "1h": "1-hour window",
        "4h": "4-hour window",
        "weekly": "Expires Friday 5PM ET",
        "monthly": "First to last day of month",
    }

    @classmethod
    def parse(cls, instrument: dict) -> Optional[dict]:
        """Parse a crypto instrument and return structured market info."""
        metadata = instrument.get("metadata", {})

        # Must be crypto price market (CRY + cpc)
        if metadata.get("event_category") != "CRY":
            return None
        if metadata.get("instrument_product") != "cpc":
            return None

        market_type = metadata.get("crypto_market_type")
        horizon = metadata.get("crypto_horizon", "")

        family_desc, structure = cls.MARKET_FAMILIES.get(market_type, ("Unknown", ""))
        horizon_desc = cls.HORIZONS.get(horizon, f"Horizon: {horizon}")

        return {
            "asset": metadata.get("event_subcategory", ""),  # BTC, ETH, etc.
            "family": market_type or "unknown",
            "family_description": family_desc,
            "structure": structure,
            "horizon": horizon,
            "horizon_description": horizon_desc,
            "outcome_strike": metadata.get("outcome_strike", ""),
            "interval_start": metadata.get("interval_start"),
            "interval_end": metadata.get("interval_end"),
            "price_to_beat": metadata.get("price_to_beat"),  # Up/down only
            "crypto_range_lower": metadata.get("crypto_range_lower"),
            "crypto_range_upper": metadata.get("crypto_range_upper"),
            "crypto_hit_direction": metadata.get("crypto_hit_direction"),
            "event_id": metadata.get("event_id", ""),
            "symbol": instrument.get("symbol", ""),
        }

    @classmethod
    def is_interesting(cls, parsed: dict) -> bool:
        """Determine if a crypto market is worth trading."""
        # Focus on updown (short windows = more frequent opportunities)
        return parsed["family"] in ("updown", "strike") and parsed.get("horizon") in ("15m", "1h")
