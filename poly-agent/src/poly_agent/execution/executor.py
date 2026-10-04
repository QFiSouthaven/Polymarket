"""Trade Executor — Polymarket Exchange (polymarket.us) API client.

Supports:
- JWT authentication via RSA key pair → Auth0 access token
- REST API for orders, portfolio, account balances
- WebSocket streaming for real-time market data and private updates
- Pre-production and production environments
"""

import asyncio
import base64
import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import jwt
import requests
from cryptography.hazmat.primitives import serialization
from loguru import logger


class TokenManager:
    """Manages JWT access tokens for Polymarket Exchange authentication."""

    def __init__(self, auth_config: dict):
        self.auth = auth_config
        self.env = auth_config.get("environment", "preprod")
        self.client_id = auth_config["client_id"]
        self.audience = auth_config["audience"]
        self.private_key_path = Path(auth_config["private_key_path"])
        self.token: Optional[str] = None
        self.expires_at: float = 0

    def _load_private_key(self) -> bytes:
        """Load RSA private key from PEM file."""
        if not self.private_key_path.exists():
            raise FileNotFoundError(f"Private key not found: {self.private_key_path}")
        with open(self.private_key_path, "rb") as f:
            return f.read()

    def _create_client_assertion(self) -> str:
        """Create and sign JWT client assertion for Auth0."""
        private_key = self._load_private_key()
        now = int(time.time())
        claims = {
            "iss": self.client_id,
            "sub": self.client_id,
            "aud": f"https://pmx-{self.env}.us.auth0.com/oauth/token",
            "iat": now,
            "exp": now + 300,  # 5 min expiry (refreshed every 150s)
            "jti": str(hashlib.sha256(str(now).encode()).hexdigest()[:16]),
        }
        return jwt.encode(claims, private_key, algorithm="RS256")

    def get_token(self) -> str:
        """Get a valid access token (refreshes if expired)."""
        if self.token and time.time() < self.expires_at - 30:
            return self.token

        assertion = self._create_client_assertion()
        auth_domain = f"pmx-{self.env}.us.auth0.com"

        response = requests.post(
            f"https://{auth_domain}/oauth/token",
            json={
                "client_id": self.client_id,
                "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
                "client_assertion": assertion,
                "audience": self.audience,
                "grant_type": "client_credentials",
            },
            timeout=10,
        )

        if response.status_code != 200:
            logger.error(f"Auth failed ({response.status_code}): {response.text}")
            raise ConnectionError(f"Authentication failed: {response.text}")

        data = response.json()
        self.token = data["access_token"]
        self.expires_at = time.time() + data.get("expires_in", 300)
        logger.debug(f"   🔑 Token refreshed (expires in {data['expires_in']}s)")
        return self.token

    def get_headers(self, method: str = "GET") -> dict:
        """Get authenticated headers for API requests."""
        token = self.get_token()
        return {"Authorization": f"Bearer {token}"}


class PolymarketExecutor:
    """Executes trades on Polymarket Exchange via REST + WebSocket APIs."""

    def __init__(self, auth_config: dict):
        self.auth_config = auth_config
        self.env = auth_config.get("environment", "preprod")
        self.token_mgr = TokenManager(auth_config)
        self.base_url = f"https://api.{self.env}.polymarketexchange.com" if self.env == "preprod" else "https://api.polymarket.us"
        # Actually: preprod uses api.preprod.polymarketexchange.com, prod uses api.polymarket.us
        if self.env == "preprod":
            self.base_url = "https://api.preprod.polymarketexchange.com"
        else:
            self.base_url = "https://api.polymarket.us"

    async def execute(self, opportunity: dict) -> dict:
        """Execute a trade based on an opportunity."""
        market_slug = opportunity["market_slug"]
        side = opportunity["side"].lower()  # "buy" or "sell"
        price = opportunity["price"]
        size_usdc = opportunity["size_usdc"]

        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._place_order(market_slug, side, price, size_usdc)
            )
            return {"success": True, "description": f"{side.upper()} {size_usdc:.2f} USDC @ ${price:.4f}", **result}

        except Exception as e:
            logger.error(f"   ❌ Trade execution failed on {market_slug}: {e}")
            return {"success": False, "error": str(e)}

    def _place_order(self, market_slug: str, side: str, price: float, size_usdc: float) -> dict:
        """Place a limit order via Polymarket Exchange REST API."""
        # Calculate quantity from USDC amount and price
        quantity = size_usdc / price if price > 0 else 0

        headers = self.token_mgr.get_headers("POST")
        headers["Content-Type"] = "application/json"

        body = {
            "marketSlug": market_slug,
            "intent": f"ORDER_INTENT_{side.upper()}_LONG",
            "type": "ORDER_TYPE_LIMIT",
            "price": {"value": str(round(price, 4)), "currency": "USD"},
            "quantity": quantity,
            "idempotency_key": str(uuid.uuid4()),  # Number Rule: idempotent on retry
        }

        response = requests.post(
            f"{self.base_url}/v1/orders",
            headers=headers,
            json=body,
            timeout=10,
        )

        if response.status_code not in (200, 201):
            logger.error(f"   ❌ Order failed ({response.status_code}): {response.text}")
            return {"success": False, "error": response.text}

        data = response.json()
        order_id = data.get("id") or data.get("orderId", "")
        logger.info(f"   ✅ Order placed: ID={order_id} | {side.upper()} {quantity:.4f} @ ${price:.4f}")
        return {"order_id": order_id, "market_slug": market_slug, "side": side.upper(), "price": price, "quantity": quantity}

    async def get_market_price(self, market_slug: str) -> Optional[float]:
        """Get current best bid/ask for a market."""
        try:
            headers = self.token_mgr.get_headers("GET")
            response = requests.get(
                f"{self.base_url}/v1/markets/{market_slug}",
                headers=headers, timeout=5,
            )
            if response.status_code == 200:
                data = response.json()
                return float(data.get("price") or 0)
        except Exception as e:
            logger.error(f"   ❌ Price fetch failed for {market_slug}: {e}")
        return None

    async def get_open_orders(self) -> list[dict]:
        """Get all open orders."""
        try:
            headers = self.token_mgr.get_headers("GET")
            response = requests.get(
                f"{self.base_url}/v1/orders/open",
                headers=headers, timeout=5,
            )
            if response.status_code == 200:
                return response.json().get("orders", [])
        except Exception as e:
            logger.error(f"   ❌ Open orders fetch failed: {e}")
        return []

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a specific order."""
        try:
            headers = self.token_mgr.get_headers("POST")
            response = requests.post(
                f"{self.base_url}/v1/order/{order_id}/cancel",
                headers=headers, timeout=5,
            )
            return response.status_code in (200, 204)
        except Exception as e:
            logger.error(f"   ❌ Cancel failed for {order_id}: {e}")
            return False

    async def cancel_all_orders(self) -> int:
        """Cancel all open orders (used during shutdown)."""
        try:
            headers = self.token_mgr.get_headers("POST")
            response = requests.post(
                f"{self.base_url}/v1/orders/open/cancel",
                headers=headers, timeout=5,
            )
            return 1 if response.status_code in (200, 204) else 0
        except Exception:
            return 0

    async def get_portfolio(self) -> dict:
        """Get current portfolio summary."""
        try:
            headers = self.token_mgr.get_headers("GET")
            positions_resp = requests.get(
                f"{self.base_url}/v1/portfolio/positions",
                headers=headers, timeout=5,
            )
            balances_resp = requests.get(
                f"{self.base_url}/v1/account/balances",
                headers=headers, timeout=5,
            )

            positions = positions_resp.json().get("positions", []) if positions_resp.status_code == 200 else []
            balances = balances_resp.json().get("balances", [{}])[0] if balances_resp.status_code == 200 else {}

            return {
                "positions": positions,
                "current_balance": balances.get("currentBalance", 0),
                "buying_power": balances.get("buyingPower", 0),
                "open_orders_value": balances.get("openOrders", 0),
            }
        except Exception as e:
            logger.error(f"   ❌ Portfolio fetch failed: {e}")
            return {}

    async def get_activities(self, limit: int = 50) -> list[dict]:
        """Get recent trading activity."""
        try:
            headers = self.token_mgr.get_headers("GET")
            response = requests.get(
                f"{self.base_url}/v1/portfolio/activities?limit={limit}&sortOrder=SORT_ORDER_DESCENDING",
                headers=headers, timeout=5,
            )
            if response.status_code == 200:
                return response.json().get("activities", [])
        except Exception as e:
            logger.error(f"   ❌ Activities fetch failed: {e}")
        return []


class WebSocketClient:
    """WebSocket client for real-time market data and private updates."""

    def __init__(self, auth_config: dict):
        self.auth = auth_config
        self.env = auth_config.get("environment", "preprod")
        if self.env == "preprod":
            self.ws_url_private = "wss://api.preprod.polymarketexchange.com/v1/ws/private"
            self.ws_url_markets = "wss://api.preprod.polymarketexchange.com/v1/ws/markets"
        else:
            self.ws_url_private = "wss://api.polymarket.us/v1/ws/private"
            self.ws_url_markets = "wss://api.polymarket.us/v1/ws/markets"

    def _get_auth_headers(self) -> dict:
        """Get WebSocket authentication headers."""
        timestamp_ms = str(int(time.time() * 1000))
        # Signature: base64(HMAC-SHA256(timestamp + "GET" + path, api_secret_key))
        # Note: Polymarket Exchange uses API key auth for WS (not JWT)
        # This requires the X-PM-Access-Key and X-PM-Timestamp headers
        return {
            "X-PM-Timestamp": timestamp_ms,
            # X-PM-Signature would be computed here with the secret key
        }

    async def subscribe_markets(self, market_slugs: list[str], callback):
        """Subscribe to real-time market data updates."""
        import websockets

        headers = self._get_auth_headers()
        subscription_msg = {
            "subscribe": {
                "request_id": f"sub-{int(time.time())}",
                "subscription_type": 1,  # MARKET_DATA (full order book)
                "market_slugs": market_slugs[:50],  # Limit per subscription
            }
        }

        try:
            async with websockets.connect(
                self.ws_url_markets, additional_headers=headers, ping_interval=30
            ) as ws:
                await ws.send(json.dumps(subscription_msg))
                logger.info(f"   📡 Subscribed to {len(market_slugs)} markets via WebSocket")

                async for message in ws:
                    data = json.loads(message)
                    if "heartbeat" in data:
                        continue  # Skip heartbeats
                    await callback(data)

        except Exception as e:
            logger.error(f"   ❌ WebSocket connection failed: {e}")

    async def subscribe_private(self, subscription_type: int, callback):
        """Subscribe to private updates (orders, positions, balances)."""
        import websockets

        headers = self._get_auth_headers()
        subscription_msg = {
            "subscribe": {
                "request_id": f"priv-{int(time.time())}",
                "subscription_type": subscription_type,  # 1=ORDER, 3=POSITION, 4=BALANCE
            }
        }

        try:
            async with websockets.connect(
                self.ws_url_private, additional_headers=headers, ping_interval=30
            ) as ws:
                await ws.send(json.dumps(subscription_msg))
                logger.info(f"   🔒 Subscribed to private stream (type={subscription_type})")

                async for message in ws:
                    data = json.loads(message)
                    if "heartbeat" in data:
                        continue
                    await callback(data)

        except Exception as e:
            logger.error(f"   ❌ Private WebSocket failed: {e}")


# Legacy compatibility wrapper (for old code that expects TradeExecutor)
class TradeExecutor(PolymarketExecutor):
    """Legacy wrapper for backward compatibility."""
    pass
