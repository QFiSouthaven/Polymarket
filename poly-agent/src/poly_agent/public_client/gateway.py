"""Public Gateway Client — fetches market data from Polymarket Exchange public API.

Base URL: https://gateway.polymarket.us (no auth required)
Endpoints: markets, events, series, sports, search
"""

import json
from typing import Optional

import requests
from loguru import logger


class PublicGatewayClient:
    """Fetches market data from Polymarket Exchange public gateway."""

    def __init__(self, environment: str = "preprod"):
        self.env = environment
        if self.env == "preprod":
            self.base_url = "https://gateway.preprod.polymarketexchange.com"
        else:
            self.base_url = "https://gateway.polymarket.us"

    def get_markets(self, limit: int = 200, closed: bool = False) -> list[dict]:
        """Fetch active markets from the public gateway."""
        url = f"{self.base_url}/v1/markets?limit={limit}&closed={str(closed).lower()}"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"   ❌ Markets fetch failed: {e}")
        return []

    def get_market_detail(self, market_slug: str) -> Optional[dict]:
        """Get detailed info for a specific market."""
        url = f"{self.base_url}/v1/markets/{market_slug}"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"   ❌ Market detail fetch failed for {market_slug}: {e}")
        return None

    def get_order_book(self, market_slug: str) -> Optional[dict]:
        """Get order book (bids/asks) for a market."""
        url = f"{self.base_url}/v1/markets/{market_slug}/book"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"   ❌ Order book fetch failed for {market_slug}: {e}")
        return None

    def get_bbo(self, market_slug: str) -> Optional[dict]:
        """Get best bid/offer for a market."""
        url = f"{self.base_url}/v1/markets/{market_slug}/bbo"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"   ❌ BBO fetch failed for {market_slug}: {e}")
        return None

    def get_events(self, limit: int = 100) -> list[dict]:
        """Fetch events (groups of markets)."""
        url = f"{self.base_url}/v1/events?limit={limit}"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"   ❌ Events fetch failed: {e}")
        return []

    def get_series(self) -> list[dict]:
        """Fetch series (e.g., NFL 2025-26 Season)."""
        url = f"{self.base_url}/v1/series"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"   ❌ Series fetch failed: {e}")
        return []

    def get_sports(self) -> dict:
        """Fetch sports leagues and teams."""
        url = f"{self.base_url}/v1/sports"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"   ❌ Sports fetch failed: {e}")
        return {}

    def search(self, query: str, limit: int = 50) -> list[dict]:
        """Full-text search across events and markets."""
        url = f"{self.base_url}/v1/search?q={query}&limit={limit}"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"   ❌ Search failed for '{query}': {e}")
        return []

    def get_health(self) -> bool:
        """Check API health."""
        try:
            response = requests.get(f"{self.base_url}/v1/health", timeout=5)
            return response.status_code == 200 and response.json().get("status") == "ok"
        except Exception:
            return False
