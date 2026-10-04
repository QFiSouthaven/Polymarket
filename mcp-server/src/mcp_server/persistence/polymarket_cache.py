"""Polymarket Cache — JSON file-based cache for Polymarket API data.

Stores cached market data, positions, prices, and order book snapshots.
Cache entries have TTL (time-to-live) to ensure freshness.
All data is stored in a local JSON file that survives server restarts.
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional


class PolymarketCache:
    """JSON-based cache for Polymarket application data."""

    def __init__(self, cache_dir: Optional[Path] = None):
        if cache_dir is None:
            self.cache_dir = Path(__file__).resolve().parent.parent / "cache"
        else:
            self.cache_dir = cache_dir
        self._data: dict[str, Any] = {}
        self._load()

    def _get_cache_file(self) -> Path:
        """Get the path to the main cache file."""
        return self.cache_dir / "polymarket_cache.json"

    def _load(self):
        """Load cache from disk."""
        cache_file = self._get_cache_file()
        if cache_file.exists():
            try:
                with open(cache_file, "r") as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._data = {}

    def _save(self):
        """Save cache to disk."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        with open(self._get_cache_file(), "w") as f:
            json.dump(self._data, f, indent=2, default=str)

    # --- Market Data Cache ---

    def get_cached_market(self, market_slug: str) -> Optional[dict]:
        """Get a cached market by slug. Returns None if expired or not found."""
        key = f"market:{market_slug}"
        entry = self._data.get(key)
        if entry is None:
            return None
        if self._is_expired(entry):
            self._remove(key)
            return None
        return entry["value"]

    def set_cached_market(self, market_slug: str, data: dict, ttl_seconds: int = 300) -> None:
        """Cache a market snapshot with TTL."""
        key = f"market:{market_slug}"
        self._data[key] = {
            "value": data,
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "ttl_seconds": ttl_seconds,
        }
        self._save()

    def invalidate_market(self, market_slug: str) -> None:
        """Invalidate a cached market entry."""
        key = f"market:{market_slug}"
        self._remove(key)

    # --- Order Book Cache ---

    def get_cached_order_book(self, market_slug: str) -> Optional[dict]:
        """Get a cached order book. TTL is shorter (60s) for live data."""
        key = f"orderbook:{market_slug}"
        entry = self._data.get(key)
        if entry is None:
            return None
        if self._is_expired(entry, default_ttl=60):
            self._remove(key)
            return None
        return entry["value"]

    def set_cached_order_book(self, market_slug: str, data: dict) -> None:
        """Cache an order book snapshot (TTL: 60s)."""
        key = f"orderbook:{market_slug}"
        self._data[key] = {
            "value": data,
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "ttl_seconds": 60,
        }
        self._save()

    # --- Price Cache ---

    def get_cached_price(self, market_slug: str) -> Optional[float]:
        """Get a cached price. TTL is very short (30s) for prices."""
        key = f"price:{market_slug}"
        entry = self._data.get(key)
        if entry is None:
            return None
        if self._is_expired(entry, default_ttl=30):
            self._remove(key)
            return None
        return entry["value"]

    def set_cached_price(self, market_slug: str, price: float) -> None:
        """Cache a price (TTL: 30s)."""
        key = f"price:{market_slug}"
        self._data[key] = {
            "value": price,
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "ttl_seconds": 30,
        }
        self._save()

    # --- Positions Cache ---

    def get_cached_positions(self) -> Optional[list[dict]]:
        """Get cached positions. TTL is moderate (120s)."""
        key = "positions"
        entry = self._data.get(key)
        if entry is None:
            return None
        if self._is_expired(entry, default_ttl=120):
            self._remove(key)
            return None
        return entry["value"]

    def set_cached_positions(self, positions: list[dict]) -> None:
        """Cache current positions (TTL: 120s)."""
        key = "positions"
        self._data[key] = {
            "value": positions,
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "ttl_seconds": 120,
        }
        self._save()

    # --- Portfolio Cache ---

    def get_cached_portfolio(self) -> Optional[dict]:
        """Get cached portfolio summary. TTL: 60s."""
        key = "portfolio"
        entry = self._data.get(key)
        if entry is None:
            return None
        if self._is_expired(entry, default_ttl=60):
            self._remove(key)
            return None
        return entry["value"]

    def set_cached_portfolio(self, portfolio: dict) -> None:
        """Cache portfolio summary (TTL: 60s)."""
        key = "portfolio"
        self._data[key] = {
            "value": portfolio,
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "ttl_seconds": 60,
        }
        self._save()

    # --- Activities Cache ---

    def get_cached_activities(self) -> Optional[list[dict]]:
        """Get cached trading activities. TTL: 300s."""
        key = "activities"
        entry = self._data.get(key)
        if entry is None:
            return None
        if self._is_expired(entry, default_ttl=300):
            self._remove(key)
            return None
        return entry["value"]

    def set_cached_activities(self, activities: list[dict]) -> None:
        """Cache trading activities (TTL: 300s)."""
        key = "activities"
        self._data[key] = {
            "value": activities,
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "ttl_seconds": 300,
        }
        self._save()

    # --- Events/Series Cache ---

    def get_cached_events(self) -> Optional[list[dict]]:
        """Get cached events. TTL: 600s (10 min)."""
        key = "events"
        entry = self._data.get(key)
        if entry is None:
            return None
        if self._is_expired(entry, default_ttl=600):
            self._remove(key)
            return None
        return entry["value"]

    def set_cached_events(self, events: list[dict]) -> None:
        """Cache events (TTL: 10 min)."""
        key = "events"
        self._data[key] = {
            "value": events,
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "ttl_seconds": 600,
        }
        self._save()

    # --- General Cache ---

    def get(self, key: str) -> Optional[Any]:
        """Get any cached value by key."""
        entry = self._data.get(key)
        if entry is None:
            return None
        if self._is_expired(entry):
            self._remove(key)
            return None
        return entry["value"]

    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        """Set any cached value with TTL."""
        self._data[key] = {
            "value": value,
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "ttl_seconds": ttl_seconds,
        }
        self._save()

    def invalidate(self, key: str) -> None:
        """Invalidate a cached entry."""
        self._remove(key)

    # --- Cache Management ---

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics (entry count, total size)."""
        return {
            "total_entries": len(self._data),
            "keys": list(self._data.keys()),
            "cache_file_size_bytes": self._get_cache_file().stat().st_size if self._get_cache_file().exists() else 0,
        }

    def clear_all(self) -> None:
        """Clear all cached data."""
        self._data = {}
        self._save()

    # --- Helpers ---

    def _is_expired(self, entry: dict, default_ttl: int = 300) -> bool:
        """Check if a cache entry is expired."""
        ttl = entry.get("ttl_seconds", default_ttl)
        cached_at_str = entry.get("cached_at")
        if not cached_at_str:
            return True
        try:
            cached_at = datetime.fromisoformat(cached_at_str)
            now = datetime.now(timezone.utc)
            return (now - cached_at).total_seconds() > ttl
        except (ValueError, TypeError):
            return True

    def _remove(self, key: str) -> None:
        """Remove a cache entry and save."""
        if key in self._data:
            del self._data[key]
            self._save()


# Singleton instance for convenience
_default_cache = PolymarketCache()


def get_polymarket_cache() -> PolymarketCache:
    """Get the default polymarket cache singleton."""
    return _default_cache
