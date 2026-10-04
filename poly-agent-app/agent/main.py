#!/usr/bin/env python3
"""
PolyAgent - Autonomous Polymarket Trading Agent
================================================
This agent scans markets, identifies profitable edges, places trades,
and manages positions automatically.

Usage:
    pip install -r requirements.txt
    python main.py
    
Or run from the app shell (Electron spawns this process).
"""

import os
import sys
import json
import time
import asyncio
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timedelta

# Third-party imports
import requests
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

# ===== IMPORTS =====
import sys
sys.path.insert(0, str(Path(__file__).parent))  # Allow importing core module

from core.fuse_panel import FusePanel, HardeningFixes, Severity
from core.heartbeat import HeartbeatHarness, MessageBoard, Task


# ===== CONFIGURATION =====
CONFIG_PATH = Path(__file__).parent / "config.yaml"


def load_config() -> dict:
    """Load configuration from YAML file."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f)
    # Default config
    return {
        "auth": {"client_id": "", "audience": "", "rsa_key_path": ""},
        "trading": {
            "daily_budget_usd": 50,
            "per_trade_max_usd": 20,
            "daily_loss_limit_usd": 50,
            "stop_loss_pct": 20,
            "take_profit_pct": 15,
        },
        "strategies": {"arbitrage": True, "edge_detection": True, "momentum": False, "market_making": False},
        "environments": {
            "retail_api_base": "https://api.prod.polymarketexchange.com",
            "preprod_api_base": "https://api.preprod.polymarketexchange.com",
        },
        "agent": {"scan_interval_seconds": 30, "max_concurrent_trades": 5, "auto_cashout": True},
    }


# ===== POLYMARKET API CLIENT =====
class PolymarketClient:
    """Handles all communication with the Polymarket Exchange Retail API."""

    def __init__(self, config: dict):
        self.config = config
        self.base_url = config["environments"]["retail_api_base"]
        self.session = requests.Session()
        self.token = None
        self.token_expires = 0
        self.positions = []
        self.open_orders = []

    def authenticate(self) -> bool:
        """Authenticate using JWT (RSA key or client credentials)."""
        auth = self.config.get("auth", {})
        client_id = auth.get("client_id", "")
        audience = auth.get("audience", "https://api.prod.polymarketexchange.com")
        rsa_key_path = auth.get("rsa_key_path", "")

        if not client_id or not audience:
            console.print("[yellow]⚠️  Auth credentials not configured. Set them in config.yaml or app Settings.[/]")
            return False

        try:
            # Try JWT with RSA key first (Institutional-style auth)
            if rsa_key_path and Path(rsa_key_path).exists():
                import jwt as pyjwt
                from cryptography.hazmat.primitives import serialization

                with open(rsa_key_path, "rb") as f:
                    private_key = serialization.load_pem_private_key(f.read(), password=None)

                now = int(time.time())
                payload = {
                    "iss": client_id,
                    "sub": client_id,
                    "aud": audience,
                    "iat": now,
                    "exp": now + 300,  # 5 min expiry
                    "nbf": now,
                }

                self.token = pyjwt.encode(payload, private_key, algorithm="RS256")
                console.print("[green]✓ Authenticated via RSA key JWT[/]")
                return True

            # Fallback: client credentials flow (Auth0)
            auth_url = f"{self.base_url}/v1/auth/token"
            response = self.session.post(auth_url, json={
                "client_id": client_id,
                "audience": audience,
                "grant_type": "client_credentials",
            })

            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token") or data.get("token")
                expires_in = data.get("expires_in", 3600)
                self.token_expires = time.time() + expires_in - 60  # refresh 1 min early
                console.print(f"[green]✓ Authenticated via client credentials (expires in {expires_in}s)[/]")
                return True

            console.print(f"[red]✗ Auth failed: {response.status_code}[/]")
            return False

        except Exception as e:
            console.print(f"[red]✗ Auth error: {e}[/]")
            return False

    def refresh_token_if_needed(self) -> bool:
        """Auto-refresh token before expiry."""
        if self.token and time.time() > self.token_expires:
            return self.authenticate()
        return True

    def _headers(self) -> dict:
        """Get auth headers for API requests."""
        headers = {"Content-Type": "application/json"}
        if self.refresh_token_if_needed():
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    # --- Markets ---
    def get_markets(self, limit: int = 100) -> list[dict]:
        """Get all active markets."""
        url = f"{self.base_url}/v1/markets?limit={limit}&active=true"
        try:
            resp = self.session.get(url, headers=self._headers())
            if resp.status_code == 200:
                return resp.json().get("results", []) or []
        except Exception as e:
            console.print(f"[red]Error fetching markets: {e}[/]")
        return []

    def get_market_by_slug(self, slug: str) -> Optional[dict]:
        """Get a specific market by its slug."""
        url = f"{self.base_url}/v1/market/slug/{slug}"
        try:
            resp = self.session.get(url, headers=self._headers())
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            console.print(f"[red]Error fetching market {slug}: {e}[/]")
        return None

    def get_market_book(self, slug: str) -> Optional[dict]:
        """Get order book for a market."""
        url = f"{self.base_url}/v1/markets/{slug}/book"
        try:
            resp = self.session.get(url, headers=self._headers())
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            console.print(f"[red]Error fetching book for {slug}: {e}[/]")
        return None

    def get_market_bbo(self, slug: str) -> Optional[dict]:
        """Get best bid/offer for a market."""
        url = f"{self.base_url}/v1/markets/{slug}/bbo"
        try:
            resp = self.session.get(url, headers=self._headers())
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            console.print(f"[red]Error fetching BBO for {slug}: {e}[/]")
        return None

    def get_price_history(self, slug: str) -> list[dict]:
        """Get price history for a market."""
        url = f"{self.base_url}/v1/price-history/{slug}"
        try:
            resp = self.session.get(url, headers=self._headers())
            if resp.status_code == 200:
                return resp.json().get("results", []) or []
        except Exception as e:
            console.print(f"[red]Error fetching price history for {slug}: {e}[/]")
        return []

    # --- Search ---
    def search_markets(self, query: str) -> list[dict]:
        """Search markets by keyword."""
        url = f"{self.base_url}/v1/search?q={query}"
        try:
            resp = self.session.get(url, headers=self._headers())
            if resp.status_code == 200:
                return resp.json().get("results", []) or []
        except Exception as e:
            console.print(f"[red]Search error for '{query}': {e}[/]")
        return []

    # --- Orders ---
    def create_order(self, slug: str, side: str, price: float, quantity: int) -> Optional[dict]:
        """Place a new order. side='buy' or 'sell', price in dollars (0-1)."""
        url = f"{self.base_url}/v1/orders"
        payload = {
            "market": slug,
            "side": side.upper(),  # BUY or SELL
            "price": price,
            "quantity": quantity,
            "timeInForce": "GTC",  # Good-Til-Cancelled (use GTD for day orders)
        }
        try:
            resp = self.session.post(url, json=payload, headers=self._headers())
            if resp.status_code == 201 or resp.status_code == 200:
                return resp.json()
            console.print(f"[red]Order failed ({resp.status_code}): {resp.text}[/]")
        except Exception as e:
            console.print(f"[red]Order error: {e}[/]")
        return None

    def get_open_orders(self) -> list[dict]:
        """Get all open orders."""
        url = f"{self.base_url}/v1/orders/open"
        try:
            resp = self.session.get(url, headers=self._headers())
            if resp.status_code == 200:
                return resp.json().get("results", []) or []
        except Exception as e:
            console.print(f"[red]Error fetching open orders: {e}[/]")
        return []

    def cancel_order(self, order_id: str) -> bool:
        """Cancel a specific order."""
        url = f"{self.base_url}/v1/orders/{order_id}"
        try:
            resp = self.session.delete(url, headers=self._headers())
            return resp.status_code in (200, 204)
        except Exception as e:
            console.print(f"[red]Cancel error: {e}[/]")
            return False

    def cancel_all_orders(self) -> bool:
        """Cancel all open orders."""
        url = f"{self.base_url}/v1/orders/cancel-all"
        try:
            resp = self.session.delete(url, headers=self._headers())
            return resp.status_code in (200, 204)
        except Exception as e:
            console.print(f"[red]Cancel all error: {e}[/]")
            return False

    # --- Portfolio ---
    def get_positions(self) -> list[dict]:
        """Get all positions."""
        url = f"{self.base_url}/v1/portfolio/positions"
        try:
            resp = self.session.get(url, headers=self._headers())
            if resp.status_code == 200:
                return resp.json().get("results", []) or []
        except Exception as e:
            console.print(f"[red]Error fetching positions: {e}[/]")
        return []

    def get_activities(self, limit: int = 50) -> list[dict]:
        """Get trading activity (fills, resolutions)."""
        url = f"{self.base_url}/v1/portfolio/activities?limit={limit}"
        try:
            resp = self.session.get(url, headers=self._headers())
            if resp.status_code == 200:
                return resp.json().get("results", []) or []
        except Exception as e:
            console.print(f"[red]Error fetching activities: {e}[/]")
        return []

    def get_account_balances(self) -> dict:
        """Get account balances."""
        url = f"{self.base_url}/v1/account/balances"
        try:
            resp = self.session.get(url, headers=self._headers())
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            console.print(f"[red]Error fetching balances: {e}[/]")
        return {}

    # --- Incentives ---
    def get_incentive_programs(self) -> list[dict]:
        """Get active incentive programs."""
        url = f"{self.base_url}/v1/incentives"
        try:
            resp = self.session.get(url, headers=self._headers())
            if resp.status_code == 200:
                return resp.json().get("results", []) or []
        except Exception as e:
            console.print(f"[red]Error fetching incentives: {e}[/]")
        return []

    def get_incentive_earnings(self) -> list[dict]:
        """Get earned incentive rewards."""
        url = f"{self.base_url}/v1/incentives/earnings"
        try:
            resp = self.session.get(url, headers=self._headers())
            if resp.status_code == 200:
                return resp.json().get("results", []) or []
        except Exception as e:
            console.print(f"[red]Error fetching earnings: {e}[/]")
        return []


# ===== STRATEGIES =====
@dataclass
class TradeOpportunity:
    """Represents a detected trading opportunity."""
    slug: str
    market_name: str
    strategy: str
    edge_pct: float  # Expected edge in percentage
    side: str  # BUY or SELL
    price: float
    quantity: int
    confidence: float  # 0-1, higher = more confident
    details: str = ""


class ArbitrageStrategy:
    """Find mispriced bundles (near-risk-free profit)."""

    def __init__(self):
        self.name = "Arbitrage"

    def scan(self, markets: list[dict], client: PolymarketClient) -> list[TradeOpportunity]:
        opportunities = []

        # Look for bundle arb: same event, different outcomes priced inconsistently
        events = {}
        for m in markets:
            slug = m.get("slug", "")
            outcome_type = m.get("outcomeType") or m.get("outcome_type")
            if not slug or not outcome_type:
                continue

            # Group by event (slug prefix)
            event_key = "-".join(slug.split("-")[:4])  # e.g., "nba-ny-sa-2026"
            events.setdefault(event_key, []).append(m)

        for event_slug, event_markets in events.items():
            if len(event_markets) < 3:
                continue  # Need at least 3 outcomes for arb check

            # Check if sum of all outcome prices deviates from ~1.0 (or expected total)
            prices = []
            for m in event_markets:
                current_price = m.get("currentPrice") or m.get("price")
                if current_price is not None:
                    try:
                        prices.append(float(current_price))
                    except (ValueError, TypeError):
                        pass

            if len(prices) >= 3:
                total = sum(prices)
                # If outcomes are mutually exclusive and exhaustive, sum should be ~1.0
                # Deviation indicates arb opportunity
                deviation = abs(total - 1.0)
                if deviation > 0.02:  # 2%+ deviation = potential arb
                    edge_pct = (deviation / total) * 100
                    opportunities.append(TradeOpportunity(
                        slug=event_slug,
                        market_name=f"Bundle {event_slug}",
                        strategy="Arbitrage",
                        edge_pct=edge_pct,
                        side="BUY",
                        price=min(prices),
                        quantity=1,
                        confidence=min(edge_pct / 5.0, 1.0),
                        details=f"Sum of outcomes: {total:.4f} (deviation: {deviation:.4f})"
                    ))

        return opportunities


class EdgeDetectionStrategy:
    """Compare PolyMarket prices against external data sources."""

    def __init__(self):
        self.name = "Edge Detection"

    def scan(self, markets: list[dict], client: PolymarketClient) -> list[TradeOpportunity]:
        opportunities = []

        for m in markets:
            slug = m.get("slug", "")
            current_price = m.get("currentPrice") or m.get("price")
            if not slug or current_price is None:
                continue

            try:
                price = float(current_price)
            except (ValueError, TypeError):
                continue

            # For sports markets, compare against known probabilities
            # This is a placeholder - in production, connect to external data APIs
            market_type = m.get("marketType") or ""
            sport_type = m.get("sportsMarketType") or m.get("market_sport_type", "")

            edge = 0.0
            side = "BUY" if price < 0.5 else "SELL"

            # Simple heuristic: if price is very low (<0.3) or very high (>0.7),
            # there might be an edge (in production, compare against model predictions)
            if price < 0.25:
                edge = (0.3 - price) * 100  # Potential upside
                side = "BUY"
            elif price > 0.75:
                edge = (price - 0.7) * 100  # Potential downside
                side = "SELL"

            if edge > 2.0:  # Minimum 2% edge threshold
                opportunities.append(TradeOpportunity(
                    slug=slug,
                    market_name=m.get("question") or slug[:50],
                    strategy="Edge Detection",
                    edge_pct=edge,
                    side=side,
                    price=price,
                    quantity=1,
                    confidence=min(edge / 10.0, 1.0),
                    details=f"Price: ${price:.3f}, Edge: +{edge:.1f}%"
                ))

        return opportunities


class MomentumStrategy:
    """Trend following - buy markets where price is trending up."""

    def __init__(self):
        self.name = "Momentum"

    def scan(self, markets: list[dict], client: PolymarketClient) -> list[TradeOpportunity]:
        opportunities = []

        for m in markets:
            slug = m.get("slug", "")
            if not slug:
                continue

            # Get price history and check trend
            history = client.get_price_history(slug)
            if len(history) < 5:
                continue

            try:
                prices = [float(h.get("price") or h.get("value")) for h in history[-10:]]
                if not prices:
                    continue

                # Simple momentum: last price > first of recent window
                current = prices[-1]
                baseline = prices[0]
                change_pct = ((current - baseline) / baseline) * 100

                if change_pct > 5 and current < 0.7:  # Up 5%+ but not overbought
                    opportunities.append(TradeOpportunity(
                        slug=slug,
                        market_name=m.get("question") or slug[:40],
                        strategy="Momentum",
                        edge_pct=change_pct,
                        side="BUY",
                        price=current,
                        quantity=1,
                        confidence=min(change_pct / 15.0, 1.0),
                        details=f"Trend: +{change_pct:.1f}% over last {len(prices)} ticks"
                    ))
            except (ValueError, TypeError):
                continue

        return opportunities


class MarketMakingStrategy:
    """Place limit orders on both sides to capture spread."""

    def __init__(self):
        self.name = "Market Making"

    def scan(self, markets: list[dict], client: PolymarketClient) -> list[TradeOpportunity]:
        opportunities = []

        for m in markets:
            slug = m.get("slug", "")
            if not slug:
                continue

            book = client.get_market_book(slug)
            if not book:
                continue

            try:
                bids = [float(b.get("price") or b.get("px")) for b in (book.get("bids") or [])[:5]]
                asks = [float(a.get("price") or a.get("px")) for a in (book.get("asks") or [])[:5]]

                if not bids or not asks:
                    continue

                best_bid = max(bids)
                best_ask = min(asks)
                spread = best_ask - best_bid

                # Opportunity to place limit orders inside the spread
                mid = (best_bid + best_ask) / 2
                half_spread = spread / 2

                if spread > 0.01:  # At least 1 cent spread
                    opportunities.append(TradeOpportunity(
                        slug=slug,
                        market_name=m.get("question") or slug[:40],
                        strategy="Market Making",
                        edge_pct=spread * 100,
                        side="BUY",
                        price=best_bid + half_spread * 0.5,
                        quantity=1,
                        confidence=min(spread / 0.03, 1.0),
                        details=f"Spread: ${spread:.3f}, Mid: ${mid:.3f}"
                    ))
            except (ValueError, TypeError):
                continue

        return opportunities


# ===== RISK MANAGER =====
class RiskManager:
    """Hard risk limits that cannot be overridden by strategies."""

    def __init__(self, config: dict):
        trading = config.get("trading", {})
        self.daily_budget = trading.get("daily_budget_usd", 50)
        self.per_trade_max = trading.get("per_trade_max_usd", 20)
        self.daily_loss_limit = trading.get("daily_loss_limit_usd", 50)
        self.stop_loss_pct = trading.get("stop_loss_pct", 20) / 100.0
        self.take_profit_pct = trading.get("take_profit_pct", 15) / 100.0

    def check_trade(self, trade: TradeOpportunity, current_spent: float, current_pnl: float) -> tuple[bool, str]:
        """Check if a trade passes all risk limits."""
        cost = trade.price * trade.quantity

        # Per-trade max
        if cost > self.per_trade_max:
            return False, f"Trade cost ${cost:.2f} exceeds per-trade max ${self.per_trade_max}"

        # Daily budget
        if current_spent + cost > self.daily_budget:
            return False, f"Daily budget exhausted (${current_spent:.0f}/${self.daily_budget})"

        # Daily loss limit
        if current_pnl < -self.daily_loss_limit:
            return False, f"Daily loss limit hit (-${abs(current_pnl):.2f}/-${self.daily_loss_limit})"

        return True, "OK"

    def check_auto_cashout(self, position) -> Optional[str]:
        """Check if a position should be auto-cashed out."""
        entry_price = float(position.get("entryPrice") or 0)
        current_price = float(position.get("currentPrice") or position.get("price") or 0)

        if entry_price == 0:
            return None

        pnl_pct = ((current_price - entry_price) / entry_price) * 100

        if pnl_pct >= self.take_profit_pct * 100:
            return f"TAKE PROFIT at +{pnl_pct:.1f}%"
        elif pnl_pct <= -self.stop_loss_pct * 100:
            return f"STOP LOSS at {pnl_pct:.1f}%"

        return None


# ===== AGENT ORCHESTRATOR =====
class PolyAgent:
    """Main agent that coordinates scanning, trading, and position management.
    
    Integrated with Fuse Panel (error logging/retry), Heartbeat Harness
    (periodic health checks), and Message Board (task/to-do list).
    """

    def __init__(self):
        self.config = load_config()
        self.client = PolymarketClient(self.config)
        self.risk_manager = RiskManager(self.config)
        
        # Operational resilience layer
        self.fuse_panel = FusePanel()  # Error logging, retry queues, circuit breakers
        self.heartbeat = HeartbeatHarness(fuse_panel=self.fuse_panel, agent=self)  # Periodic health checks
        self.message_board = MessageBoard()  # Task/to-do list for the agent
        self.strategies = {}

        # Initialize strategies based on config
        if self.config["strategies"].get("arbitrage"):
            self.strategies["arb"] = ArbitrageStrategy()
        if self.config["strategies"].get("edge_detection"):
            self.strategies["edge"] = EdgeDetectionStrategy()
        if self.config["strategies"].get("momentum"):
            self.strategies["mom"] = MomentumStrategy()
        if self.config["strategies"].get("market_making"):
            self.strategies["mm"] = MarketMakingStrategy()

        # State
        self.running = False
        self.daily_spent = 0.0
        self.daily_pnl = 0.0
        self.active_trades = []
        self.trades_today = 0

    def start(self):
        """Start the agent with full operational resilience layer."""
        console.print(Panel("[bold green]🤖 PolyAgent Starting (with Fuse Panel + Heartbeat)[/]", border_style="green"))
        
        # Start heartbeat harness
        self.heartbeat.start()
        
        # Log initial state to message board
        self.message_board.add_task(
            "PolyAgent startup - all systems nominal",
            priority=1, category="system"
        )

        # Authenticate
        if not self.client.authenticate():
            console.print("[yellow]⚠️  Auth failed. Agent will run in demo mode.[/]")
            return False

        # Load positions
        self.active_trades = self.client.get_positions()
        activities = self.client.get_activities(limit=10)
        for act in activities:
            if act.get("type") == "FILL":
                self.daily_spent += float(act.get("notional", 0))
            elif act.get("type") == "RESOLUTION":
                self.daily_pnl += float(act.get("pnl", 0))

        console.print(f"[green]✓ Loaded {len(self.active_trades)} active positions[/]")
        console.print(f"[cyan]📊 Daily: spent=${self.daily_spent:.2f}, P&L=${self.daily_pnl:.2f}[/]")

        self.running = True
        return True

    def stop(self):
        """Stop the agent gracefully with cleanup."""
        self.running = False
        self.heartbeat.stop()
        self.message_board.add_task(
            f"PolyAgent stopped (trades today: {self.trades_today})",
            priority=2, category="system"
        )
        console.print("[yellow]⏹ Agent stopped.[/]")

    def scan_markets(self) -> list[TradeOpportunity]:
        """Run all enabled strategies against current markets."""
        if not self.client.refresh_token_if_needed():
            return []

        # Get fresh market data
        markets = self.client.get_markets(limit=200)
        if not markets:
            console.print("[yellow]⚠️  No markets returned from API[/]")
            return []

        all_opportunities = []

        for name, strategy in self.strategies.items():
            opportunities = strategy.scan(markets, self.client)
            all_opportunities.extend(opportunities)
            if opportunities:
                console.print(f"[blue]  {strategy.name}: found {len(opportunities)} opportunities[/]")

        # Sort by confidence (highest first)
        all_opportunities.sort(key=lambda x: x.confidence, reverse=True)
        return all_opportunities

    def execute_trade(self, opportunity: TradeOpportunity) -> bool:
        """Execute a trade if it passes risk checks."""
        # Check risk limits
        can_trade, reason = self.risk_manager.check_trade(
            opportunity, self.daily_spent, self.daily_pnl
        )

        if not can_trade:
            console.print(f"[yellow]  ✗ Rejected: {reason}[/]")
            return False

        # Execute the order
        result = self.client.create_order(
            slug=opportunity.slug,
            side=opportunity.side,
            price=opportunity.price,
            quantity=opportunity.quantity
        )

        if result:
            self.daily_spent += opportunity.price * opportunity.quantity
            self.trades_today += 1
            console.print(f"[green]  ✓ Executed: {opportunity.market_name} ({opportunity.side} @ ${opportunity.price:.3f})[/]")
            return True

        return False

    def check_auto_cashout(self):
        """Check all positions for auto cashout conditions."""
        if not self.config["agent"].get("auto_cashout", True):
            return

        positions = self.client.get_positions()
        for pos in positions:
            reason = self.risk_manager.check_auto_cashout(pos)
            if reason:
                slug = pos.get("slug") or pos.get("market", "")
                console.print(f"[red]  ⚡ Auto-cashout triggered: {reason} on {slug}[/]")
                # Cancel order to close position (simplified - in production use close-position endpoint)

    def run_scan_cycle(self):
        """Run one complete scan cycle."""
        if not self.running:
            return

        console.print(f"\n[bold]🔍 Scan #{self.trades_today + 1}[/]")

        # Check auto cashout first
        self.check_auto_cashout()

        # Scan for opportunities
        opportunities = self.scan_markets()

        if not opportunities:
            console.print("[dim]No opportunities found this cycle.[/]\n")
            return

        # Execute top opportunities (respecting max concurrent trades)
        max_trades = self.config["agent"].get("max_concurrent_trades", 5)
        executed = 0

        for opp in opportunities:
            if executed >= max_trades or len(self.active_trades) >= max_trades:
                break

            if self.execute_trade(opp):
                executed += 1

        console.print(f"[dim]Executed {executed}/{len(opportunities)} opportunities. Active trades: {len(self.active_trades) + executed}[/]\n")

    def get_status_report(self) -> str:
        """Generate a comprehensive status report including Fuse Panel and Heartbeat."""
        positions = self.client.get_positions()
        incentives = self.client.get_incentive_earnings()
        total_earned = sum(float(e.get("amount", 0)) for e in incentives)

        # Get fuse panel status
        health = self.fuse_panel.check_health()
        retry_status = self.fuse_panel.get_retry_status()
        
        # Get heartbeat status
        hb_status = self.heartbeat.get_status()
        
        # Get message board summary
        mb_summary = self.message_board.get_task_summary()

        return (
            f"🤖 PolyAgent Status:\n"
            f"• Running: {'✅ Yes' if self.running else '❌ No'}\n"
            f"• Active trades: {len(positions)}\n"
            f"• Trades today: {self.trades_today}\n"
            f"• Daily spent: ${self.daily_spent:.2f}/${self.config['trading']['daily_budget_usd']}\n"
            f"• Daily P&L: ${self.daily_pnl:.2f}\n"
            f"• Incentive earnings: ${total_earned:.2f}\n"
            f"• Strategies active: {', '.join(self.strategies.keys())}\n"
            f"\n🔧 Fuse Panel:\n"
            f"  System health: {'✅ Healthy' if health['status'] == 'healthy' else '⚠️ Degraded'}\n"
            f"  Errors (1h): {health['errors_last_hour']} | Retries queued: {retry_status['total']}\n"
            f"\n❤️ Heartbeat:\n"
            f"  Checks run: {hb_status['check_count']} | Consecutive failures: {hb_status['consecutive_failures']}\n"
            f"\n📋 Message Board:\n{mb_summary}"
        )

    def handle_command(self, command: str) -> str:
        """Handle a text command from the chat panel.
        
        Integrates with Message Board (adds tasks), Fuse Panel (logs errors),
        and Heartbeat Harness (triggers health checks).
        """
        cmd = command.lower().strip()

        # Add to message board as a task
        self.message_board.add_agent_task(command)

        if cmd == "scan":
            self.run_scan_cycle()
            return self.get_status_report()

        elif cmd.startswith("scan "):
            sport = cmd[5:].upper()
            markets = self.client.search_markets(sport)
            return f"🔍 Found {len(markets)} {sport} markets. Scanning for opportunities...\n{self.run_scan_cycle()}"

        elif cmd == "stop":
            self.stop()
            return "⏹ Agent stopped."

        elif cmd.startswith("set budget"):
            try:
                amount = int(cmd.split("$")[1].split("/")[0])
                self.config["trading"]["daily_budget_usd"] = amount
                return f"✅ Budget set to ${amount}/day."
            except (IndexError, ValueError):
                return "❌ Usage: 'set budget $50'"

        elif cmd == "positions":
            positions = self.client.get_positions()
            if not positions:
                return "📊 No active positions."
            lines = [f"📊 Active Positions ({len(positions)}):"]
            for p in positions[:10]:
                name = p.get("slug", "")[:40]
                pnl = p.get("pnl", 0)
                lines.append(f"  • {name}: ${float(pnl):+.2f}")
            return "\n".join(lines)

        elif cmd == "status":
            return self.get_status_report()

        # Message Board commands
        elif cmd.startswith("tasks") or cmd == "todo" or cmd == "board":
            return self.message_board.get_task_summary()

        elif cmd.startswith("add task"):
            title = command[9:].strip() if len(command) > 8 else "Untitled"
            task = self.message_board.add_task(title, priority=5)
            return f"✅ Task added: '{task.title}' (ID: {task.id})\nPriority: {task.priority} | Status: {task.status}"

        elif cmd.startswith("complete"):
            parts = command.split()
            if len(parts) > 1:
                task_id = parts[1]
                if self.message_board.complete_task(task_id):
                    return f"✅ Task completed."
            return "❌ Usage: 'complete <task_id>' or 'tasks' to list them."

        # Fuse Panel commands
        elif cmd == "fuse" or cmd == "errors":
            return self.fuse_panel.get_status_report()

        elif cmd == "retry":
            status = self.fuse_panel.get_retry_status()
            lines = [f"🔄 Retry Queue ({status['total']} tasks):"]
            if status["entries"]:
                for e in status["entries"][:10]:
                    lines.append(f"  • {e['source']} (attempt {e['attempt']}/{5})")
            else:
                lines.append("  Queue is empty.")
            return "\n".join(lines)

        # Heartbeat commands
        elif cmd == "heartbeat":
            status = self.heartbeat.get_status()
            return (
                f"❤️ Heartbeat Status:\n"
                f"• Running: {'Yes' if status['running'] else 'No'}\n"
                f"• Checks run: {status['check_count']}\n"
                f"• Interval: {status['interval_seconds']}s\n"
                f"• Consecutive failures: {status['consecutive_failures']}\n"
                f"• Scheduled tasks: {list(status['scheduled_tasks'].keys())}"
            )

        elif cmd.startswith("schedule"):
            parts = command.split()
            if len(parts) >= 3:
                name = parts[1]
                try:
                    interval = int(parts[2])
                    self.heartbeat.add_scheduled_task(name, interval)
                    return f"✅ Scheduled '{name}' to run every {interval}s"
                except ValueError:
                    return "❌ Usage: 'schedule <name> <seconds>' (e.g., 'schedule scan_markets 60')"
            return "❌ Usage: 'schedule <task_name> <interval_seconds>'"

        else:
            return (
                f"🤖 I received: '{command}'\n\n"
                f"Try:\n"
                f"  • 'scan' - scan all markets\n"
                f"  • 'scan NFL' - scan specific sport\n"
                f"  • 'set budget $50' - set daily limit\n"
                f"  • 'positions' - view trades\n"
                f"  • 'stop' - pause agent"
            )


# ===== MAIN ENTRY POINT =====
def main():
    """Main entry point. Can be run standalone or spawned by Electron."""
    import signal

    agent = PolyAgent()

    # Handle signals for graceful shutdown
    def handle_signal(sig, frame):
        console.print("\n[yellow]Received shutdown signal.[/]")
        agent.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # Start agent
    if not agent.start():
        console.print("[red]Failed to start. Check config.yaml for auth credentials.[/]")
        sys.exit(1)

    # Main loop - runs heartbeat + scanning
    scan_interval = agent.config["agent"].get("scan_interval_seconds", 30)
    last_heartbeat = time.time()

    try:
        while agent.running:
            now = time.time()
            
            # Run heartbeat cycle every interval seconds
            if now - last_heartbeat >= agent.heartbeat.interval_seconds:
                hb_result = agent.heartbeat.run_cycle()
                last_heartbeat = now
            
            # Scan markets on schedule
            agent.run_scan_cycle()
            time.sleep(scan_interval)
    except KeyboardInterrupt:
        agent.stop()


if __name__ == "__main__":
    main()
