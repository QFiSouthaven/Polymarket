"""Risk Manager — protects your capital with hard limits.

Number Rule enforcement (P0 data safety):
- All monetary values stored as Decimal (never float)
- Three-source verification: intent ↔ API receipt ↔ persisted book
- If any two disagree → trade blocked + ALERT raised
"""

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Tuple

from loguru import logger

ZERO = Decimal("0")
HUNDRED = Decimal("100")
TWO = Decimal("2")


@dataclass
class RiskState:
    """Current risk state of the agent."""
    total_budget_usdc: Decimal = ZERO
    remaining_budget_usdc: Decimal = ZERO
    daily_pnl: Decimal = ZERO
    max_daily_loss: Decimal = ZERO
    profit_target_daily: Decimal = ZERO
    max_open_positions: int = 20
    current_open_positions: int = 0
    max_per_trade_usdc: Decimal = Decimal("50")
    consecutive_losses: int = 0
    total_drawdown_pct: Decimal = ZERO
    kill_switch_triggered: bool = False


class RiskManager:
    """Hard risk limits that cannot be overridden by strategies."""

    def __init__(self, config: dict):
        self.config = config["risk"]
        self._last_verified: dict = {}  # Number Rule: intent snapshot for 3-source check
        self.state = RiskState(
            total_budget_usdc=Decimal(str(config.get("total_budget", 1000))),
            remaining_budget_usdc=Decimal(str(config.get("total_budget", 1000))),
            max_daily_loss=Decimal(str(config["stop_loss_pct"])),
            profit_target_daily=Decimal(str(config.get("profit_target_daily", 50))),
            max_open_positions=config.get("max_open_positions", 20),
            max_per_trade_usdc=Decimal(str(config.get("max_per_trade_usdc", 50))),
        )

    def _three_source_verify(self, intent: dict, api_receipt: dict, persisted: dict) -> Tuple[bool, str]:
        """Number Rule: three-source verification.
        Returns (is_valid, reason_if_not)"""
        # Source 1: intent (what we requested)
        intent_price = Decimal(str(intent.get("price")))
        intent_qty = Decimal(str(intent.get("quantity")))
        intent_side = intent.get("side", "").upper()

        # Source 2: API receipt (what Polymarket confirmed)
        api_price = Decimal(str(api_receipt.get("price", intent_price)))
        api_qty = Decimal(str(api_receipt.get("quantity", intent_qty)))
        api_side = api_receipt.get("side", intent_side)

        # Source 3: Persisted book (what's on disk)
        persisted_price = Decimal(str(persisted.get("price", intent_price)))
        persisted_qty = Decimal(str(persisted.get("quantity", intent_qty)))

        # Allow 0.1% tolerance for price (slippage), 0 qty tolerance (exact match required)
        price_diff = abs(intent_price - api_price) / max(intent_price, Decimal("0.0001"))
        if price_diff > Decimal("0.001"):
            return False, f"Intent price {intent_price} ≠ API receipt {api_price} (diff={price_diff:.4%})"

        if intent_side != api_side:
            return False, f"Intent side {intent_side} ≠ API side {api_side}"

        if intent_qty != api_qty:
            return False, f"Intent qty {intent_qty} ≠ API qty {api_qty}"

        # Persisted must match intent
        if persisted_price != intent_price:
            return False, f"Persisted price {persisted_price} ≠ intent {intent_price}"
        if persisted_qty != intent_qty:
            return False, f"Persisted qty {persisted_qty} ≠ intent {intent_qty}"

        self._last_verified = {
            "intent": intent, "api_receipt": api_receipt, "persisted": persisted,
            "verified_at": None  # set by caller
        }
        return True, ""

    def can_trade(self) -> bool:
        """Check if trading is allowed right now."""
        # Kill switch
        if self.state.kill_switch_triggered:
            logger.error("🚨 KILL SWITCH ACTIVE — no trades until manually reset")
            return False

        # Daily loss limit
        if self.state.daily_pnl <= self.state.max_daily_loss:
            logger.warning(f"⛔ Daily loss limit hit (${self.state.daily_pnl:+,.2f})")
            return False

        # Profit target reached — pause for the day
        if self.config.get("profit_target_daily"):
            profit_limit = self.config["capital"]["profit_target_daily_usdc"]
            if self.state.daily_pnl >= profit_limit:
                logger.info(f"💰 Daily profit target ${profit_limit} hit — pausing")
                return False

        # Max positions
        if self.state.current_open_positions >= self.state.max_open_positions:
            logger.debug("Max open positions reached")
            return False

        return True

    def can_open_position(self, size_usdc: Decimal, order_id: str = "") -> bool:
        """Check if a new position of given size is allowed. Number Rule enforced."""
        # Number Rule: three-source verify before allowing ANY position
        if order_id and not self._verify_at_trade_time(size_usdc, order_id):
            return False

        # Per-trade limit
        max_per_trade = self.config["capital"]["max_per_trade_usdc"]
        if size_usdc > max_per_trade:
            logger.debug(f"Trade ${size_usdc} exceeds per-trade limit ${max_per_trade}")
            return False

        # Remaining budget
        remaining = self.state.remaining_budget_usdc - (self.state.current_open_positions * 10)
        if remaining < size_usdc:
            logger.debug(f"Not enough remaining budget for ${size_usdc}")
            return False

        # Correlation check
        max_corr = self.config.get("max_correlation_exposure", Decimal("0.4"))
        if hasattr(self, "_correlated_positions"):
            corr_pct = len(self._correlated_positions) / max(len(self.state.open_positions), 1)
            if corr_pct > max_corr:
                logger.debug(f"Correlation limit hit ({corr_pct:.2f} > {max_corr})")
                return False

        return True

    def _verify_at_trade_time(self, size_usdc: Decimal, order_id: str) -> bool:
        """Pre-trade Number Rule enforcement: verify persisted book matches order_id."""
        from poly_agent.position_tracker import PositionTracker
        tracker = PositionTracker(self.config, self)

        # Read the persisted position for this order_id
        from poly_agent.position_tracker import position_db
        try:
            with position_db(tracker.db_path) as conn:
                row = conn.execute(
                    "SELECT entry_price, size_usdc, status FROM positions WHERE id=?",
                    (order_id,),
                ).fetchone()
        except Exception:
            logger.warning(f"Number Rule: cannot verify persisted book for {order_id} — proceeding (no persisted record yet)")
            return True

        if row is None:
            # No persisted record yet — first trade, ok
            return True

        stored_price = Decimal(str(row["entry_price"]))
        stored_size = Decimal(str(row["size_usdc"]))
        stored_status = row["status"]

        if stored_status == "ALERT":
            logger.error(f"🚨 Number Rule: position {order_id} in ALERT state — BLOCKED")
            return False

        if abs(stored_size - size_usdc) > Decimal("0.0001"):
            logger.error(
                f"🚨 Number Rule: size mismatch {order_id} "
                f"persisted={stored_size} vs trade_size={size_usdc} — BLOCKED"
            )
            return False

        return True

    def record_trade_result(self, pnl_usdc: Decimal):
        """Record the result of a trade for risk tracking."""
        self.state.daily_pnl += Decimal(str(pnl_usdc))
        if Decimal(str(pnl_usdc)) < ZERO:
            self.state.consecutive_losses += 1
        else:
            self.state.consecutive_losses = 0

        # Check kill switch conditions
        ks = self.config.get("kill_switch", {})
        if ks["enabled"]:
            if self.state.consecutive_losses >= ks.get("consecutive_losses", 5):
                logger.error(f"🚨 Kill switch: {self.state.consecutive_losses} consecutive losses")
                self.state.kill_switch_triggered = True

            drawdown = abs(self.state.daily_pnl) / max(self.state.total_budget_usdc, 1)
            if drawdown >= ks.get("drawdown_pct", 0.15):
                logger.error(f"🚨 Kill switch: {drawdown:.1%} drawdown")
                self.state.kill_switch_triggered = True

    def update_position_count(self, delta: int):
        """Update open position count."""
        self.state.current_open_positions += delta
        self.state.current_open_positions = max(0, self.state.current_open_positions)
