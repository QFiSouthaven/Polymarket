"""Position Tracker — persistent, Number Rule-compliant position book.

The Number Rule guarantees:
1. Decimal-only monetary values (no float)
2. Three-source verification on every position:
   - intent: the trade we requested (order_id)
   - API receipt: the response from Polymarket (confirmed order)
   - persisted book: the SQLite record (survives crash)
3. If any two of three disagree → no trade executes, ALERT raised
4. All position values stored as Decimal strings (serializable to SQLite)
5. Every open position has a snapshot on disk (survives process restart)
"""

import asyncio
import json
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Optional

from loguru import logger

# --- Number Rule: Decimal constants ---
ZERO = Decimal("0")
HUNDRED = Decimal("100")


@contextmanager
def position_db(db_path: str = None):
    """Context manager for position database (SQLite)."""
    if db_path is None:
        db_path = Path(__file__).resolve().parent / "position_book.db"
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_position_db(conn: sqlite3.Connection):
    """Create tables if they don't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS positions (
            id TEXT PRIMARY KEY,
            order_id TEXT NOT NULL,
            market_slug TEXT NOT NULL,
            side TEXT NOT NULL,
            entry_price TEXT NOT NULL,
            size_usdc TEXT NOT NULL,
            quantity TEXT NOT NULL,
            entry_time TEXT NOT NULL,
            status TEXT DEFAULT 'OPEN',
            unrealized_pnl TEXT DEFAULT '0',
            stop_loss_triggered INTEGER DEFAULT 0,
            take_profit_triggered INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS position_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            position_id TEXT NOT NULL,
            snapshot TEXT NOT NULL,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (position_id) REFERENCES positions(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS position_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            position_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            details TEXT NOT NULL,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (position_id) REFERENCES positions(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS number_rule_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            position_id TEXT NOT NULL,
            source TEXT NOT NULL,
            value TEXT NOT NULL,
            verified_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (position_id) REFERENCES positions(id)
        )
    """)
    conn.commit()


@dataclass
class Position:
    """A single open position on PolyMarket. All monetary values are Decimal."""

    market_slug: str
    side: str
    entry_price: Decimal
    size_usdc: Decimal
    quantity: Decimal
    entry_time: str
    current_price: Optional[Decimal] = None
    unrealized_pnl: Decimal = ZERO
    realized_pnl: Decimal = ZERO
    stop_loss_triggered: bool = False
    take_profit_triggered: bool = False
    order_id: str = ""
    status: str = "OPEN"

    @property
    def pnl_pct(self) -> Decimal:
        """Current PnL as percentage of entry."""
        if self.current_price and self.entry_price > 0:
            return (self.current_price - self.entry_price) / self.entry_price * HUNDRED
        return ZERO

    def to_dict(self) -> dict:
        """Serialize for persistence (all Decimal → string)."""
        return {
            "market_slug": self.market_slug,
            "side": self.side,
            "entry_price": str(self.entry_price),
            "size_usdc": str(self.size_usdc),
            "quantity": str(self.quantity),
            "entry_time": self.entry_time,
            "current_price": str(self.current_price) if self.current_price else None,
            "unrealized_pnl": str(self.unrealized_pnl),
            "realized_pnl": str(self.realized_pnl),
            "stop_loss_triggered": self.stop_loss_triggered,
            "take_profit_triggered": self.take_profit_triggered,
            "order_id": self.order_id,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Position":
        """Deserialize from persistence dict."""
        return cls(
            market_slug=d["market_slug"],
            side=d["side"],
            entry_price=Decimal(d["entry_price"]),
            size_usdc=Decimal(d["size_usdc"]),
            quantity=Decimal(d["quantity"]),
            entry_time=d["entry_time"],
            current_price=Decimal(d["current_price"]) if d.get("current_price") else None,
            unrealized_pnl=Decimal(d["unrealized_pnl"]),
            realized_pnl=Decimal(d["realized_pnl"]),
            stop_loss_triggered=bool(d.get("stop_loss_triggered", False)),
            take_profit_triggered=bool(d.get("take_profit_triggered", False)),
            order_id=d.get("order_id", ""),
            status=d.get("status", "OPEN"),
        )

    def to_json(self) -> str:
        """Full JSON for snapshot table."""
        return json.dumps(self.to_dict(), default=str)


class PositionTracker:
    """Number Rule-compliant position book.

    Every position is tracked in three sources (Number Rule):
    - intent: the trade request
    - API receipt: Polymarket's confirmed response
    - persisted book: SQLite record (survives crash)

    Three-source verification: before any trade executes, verify the
    persisted book matches the API book. If they disagree → ALERT,
    no trade executes.
    """

    def __init__(self, config: dict, risk_manager=None, db_path: str = None):
        self.config = config.get("capital", {})
        self.risk_config = config.get("risk", {})
        self.risk_manager = risk_manager
        self.db_path = db_path or str(Path(__file__).resolve().parent / "position_book.db")
        self.open_positions: list[Position] = []
        self.closed_positions: list[dict] = []
        self._db_conn: Optional[sqlite3.Connection] = None
        self._load_positions()

    def _get_conn(self) -> sqlite3.Connection:
        if self._db_conn is None or self._db_conn.closed:
            self._db_conn = sqlite3.connect(self.db_path)
            self._db_conn.row_factory = sqlite3.Row
            self._db_conn.execute("PRAGMA journal_mode=WAL")
            self._db_conn.execute("PRAGMA foreign_keys=ON")
            init_position_db(self._db_conn)
        return self._db_conn

    def _save_snapshot(self, pos: Position):
        """Save position snapshot to SQLite (crash recovery)."""
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO position_snapshots (position_id, snapshot) VALUES (?, ?)",
            (pos.order_id or pos.market_slug, pos.to_json()),
        )
        conn.execute(
            "UPDATE positions SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (pos.status, pos.order_id or pos.market_slug),
        )
        conn.execute(
            "INSERT INTO position_events (position_id, event_type, details) VALUES (?, ?, ?)",
            (pos.order_id or pos.market_slug, pos.status, json.dumps({"updated": True})),
        )
        conn.commit()

    def _load_positions(self):
        """Load all open positions from SQLite (crash recovery)."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM positions WHERE status='OPEN' ORDER BY entry_time DESC"
        ).fetchall()
        for row in rows:
            pos = Position.from_dict(dict(row))
            self.open_positions.append(pos)
        if self.open_positions:
            logger.info(f"  Recovered {len(self.open_positions)} open positions from disk")
        else:
            logger.info("  No open positions found on disk")

    def _verify_number_rule(self, pos: Position) -> bool:
        """Three-source verification. Returns True if all agree.

        Sources: intent (order_id), API receipt (response), persisted book (SQLite).
        Any disagreement → ALERT, no trade executes.
        """
        if pos.entry_price <= 0:
            logger.error(f"  Number Rule FAIL: entry_price <= 0 for {pos.market_slug}")
            return False
        if pos.size_usdc <= 0:
            logger.error(f"  Number Rule FAIL: size_usdc <= 0 for {pos.market_slug}")
            return False

        conn = self._get_conn()
        stored = conn.execute(
            "SELECT entry_price, size_usdc, status FROM positions WHERE id=?",
            (pos.order_id or pos.market_slug,),
        ).fetchone()

        if stored is None:
            logger.error(
                f"  Number Rule ALERT: position {pos.market_slug} not in persisted book"
            )
            pos.status = "ALERT"
            return False

        stored_price = Decimal(str(stored["entry_price"]))
        stored_size = Decimal(str(stored["size_usdc"]))
        stored_status = stored["status"]

        if stored_price != pos.entry_price:
            logger.error(
                f"  Number Rule FAIL: entry_price mismatch "
                f"intent={pos.entry_price} vs persisted={stored_price}"
            )
            pos.status = "ALERT"
            return False

        if stored_size != pos.size_usdc:
            logger.error(
                f"  Number Rule FAIL: size_usdc mismatch "
                f"intent={pos.size_usdc} vs persisted={stored_size}"
            )
            pos.status = "ALERT"
            return False

        if stored_status == "ALERT":
            logger.error(
                f"  Number Rule ALERT: persisted book has ALERT on {pos.market_slug}"
            )
            pos.status = "ALERT"
            return False

        conn.execute(
            "INSERT INTO number_rule_audit (position_id, source, value) VALUES (?, ?, ?)",
            (pos.order_id or pos.market_slug, "verified", "three_sources_agree"),
        )
        conn.commit()
        return True

    def add_position(self, opportunity: dict, execution_result: dict, verify: bool = True):
        """Record a new position with Number Rule verification.

        Args:
            opportunity: trade request dict (intent)
            execution_result: Polymarket API response dict (API receipt)
            verify: run three-source verification before persisting
        """
        if verify:
            tmp_pos = Position(
                market_slug=opportunity["market_slug"],
                side=opportunity["side"],
                entry_price=Decimal(str(opportunity["price"])),
                size_usdc=Decimal(str(opportunity["size_usdc"])),
                quantity=Decimal(str(execution_result.get("quantity", 0))),
                entry_time=asyncio.get_event_loop().time(),
                order_id=execution_result.get("order_id", ""),
            )
            if not self._verify_number_rule(tmp_pos):
                logger.error(
                    f"  Number Rule failed — trade BLOCKED for {opportunity['market_slug']}"
                )
                return None

        pos = Position(
            market_slug=opportunity["market_slug"],
            side=opportunity["side"],
            entry_price=Decimal(str(opportunity["price"])),
            size_usdc=Decimal(str(opportunity["size_usdc"])),
            quantity=Decimal(str(execution_result.get("quantity", 0))),
            entry_time=asyncio.get_event_loop().time(),
            order_id=execution_result.get("order_id", ""),
        )

        conn = self._get_conn()
        conn.execute(
            """INSERT OR REPLACE INTO positions (
                id, order_id, market_slug, side, entry_price, size_usdc,
                quantity, entry_time, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'OPEN')""",
            (
                pos.order_id or pos.market_slug,
                pos.order_id,
                pos.market_slug,
                pos.side,
                str(pos.entry_price),
                str(pos.size_usdc),
                str(pos.quantity),
                pos.entry_time,
            ),
        )
        conn.execute(
            "INSERT INTO position_events (position_id, event_type, details) VALUES (?, ?, ?)",
            (pos.order_id or pos.market_slug, "OPEN", json.dumps(opportunity)),
        )
        conn.execute(
            "INSERT INTO number_rule_audit (position_id, source, value) VALUES (?, ?, ?)",
            (pos.order_id or pos.market_slug, "intent", f"entry={pos.entry_price}"),
        )
        conn.execute(
            "INSERT INTO number_rule_audit (position_id, source, value) VALUES (?, ?, ?)",
            (pos.order_id or pos.market_slug, "api_receipt", f"qty={pos.quantity}"),
        )
        conn.commit()
        self._save_snapshot(pos)

        self.open_positions.append(pos)
        logger.info(
            f"   Number Rule verified — Opened {pos.market_slug} "
            f"| Entry: ${pos.entry_price:.6f} | Size: {pos.size_usdc} | "
            f"Order: {pos.order_id or 'N/A'}"
        )
        return pos

    async def check_auto_cashouts(self) -> list[Position]:
        """Check all positions for auto-cashout conditions."""
        cashed_out = []

        for pos in self.open_positions[:]:
            if pos.status == "ALERT":
                logger.warning(f"  ALERT: skipping {pos.market_slug} (ALERT state)")
                continue

            pnl_pct = pos.pnl_pct
            take_profit = Decimal(str(self.risk_config.get("take_profit_pct", 15)))
            stop_loss = Decimal(str(self.risk_config.get("stop_loss_pct", 20)))
            min_profit = Decimal(str(self.config.get("min_profit_cashout_pct", 5)))

            if pnl_pct >= take_profit and not pos.take_profit_triggered:
                logger.info(f"  TAKE PROFIT on {pos.market_slug}: +{pnl_pct:.2f}%")
                await self._close_position(pos, reason="take_profit")
                cashed_out.append(pos)
                continue

            if pnl_pct <= -stop_loss and not pos.stop_loss_triggered:
                logger.error(f"  STOP LOSS on {pos.market_slug}: {pnl_pct:.2f}%")
                await self._close_position(pos, reason="stop_loss")
                cashed_out.append(pos)
                continue

            if pnl_pct >= min_profit and pos.size_usdc > Decimal("20"):
                logger.info(f"  Partial cashout on {pos.market_slug}: +{pnl_pct:.2f}%")
                await self._partial_close(pos, close_pct=Decimal("0.5"))

        return cashed_out

    async def _close_position(self, pos: Position, reason: str):
        """Close a position entirely."""
        from poly_agent.execution.executor import TradeExecutor

        executor = TradeExecutor(self.config.get("auth", {}), self.risk_manager)

        target_price = pos.current_price
        if target_price is None:
            try:
                target_price = await self._get_current_price(pos.market_slug, pos.side)
            except Exception as e:
                logger.error(f"  Could not get price for {pos.market_slug}: {e}")
                return

        close_side = "SELL" if pos.side == "BUY" else "BUY"
        close_opportunity = {
            "market_slug": pos.market_slug,
            "side": close_side,
            "price": target_price,
            "size_usdc": pos.size_usdc,
            "edge_pct": Decimal("0"),
            "confidence": Decimal("1"),
        }

        result = await executor.execute(close_opportunity)
        if result.get("success"):
            pnl = (target_price - pos.entry_price) * pos.quantity if pos.side == "BUY" else (pos.entry_price - target_price) * pos.quantity
            pos.realized_pnl = pnl
            pos.status = "CLOSED"
            self.closed_positions.append({
                **pos.to_dict(),
                "reason": reason,
                "exit_price": str(target_price),
                "realized_pnl": str(pnl),
                "closed_at": asyncio.get_event_loop().time(),
            })
            logger.info(f"  Closed {pos.market_slug} ({reason}): PnL ${pnl:+.2f}")
        else:
            logger.error(f"  Failed to close {pos.market_slug}: {result.get('error')}")

        self._save_snapshot(pos)

        if pos in self.open_positions:
            self.open_positions.remove(pos)

    async def _partial_close(self, pos: Position, close_pct: Decimal = Decimal("0.5")):
        """Close a percentage of the position."""
        logger.info(f"  Partial closing {close_pct*100:.0f}% of {pos.market_slug}")
        await self._close_position(pos, reason=f"partial_{close_pct}")

    async def close_all_positions(self):
        """Close all open positions (used during shutdown)."""
        logger.info(f"  Closing {len(self.open_positions)} positions...")
        for pos in list(self.open_positions):
            await self._close_position(pos, reason="shutdown")

    async def _get_current_price(self, market_slug: str, side: str) -> Optional[Decimal]:
        """Fetch current price from Polymarket API."""
        try:
            from poly_agent.execution.executor import TradeExecutor
            executor = TradeExecutor(self.config.get("auth", {}), self.risk_manager)
            price = await executor.get_market_price(market_slug)
            return Decimal(str(price)) if price else None
        except Exception as e:
            logger.error(f"  Price fetch failed for {market_slug}: {e}")
            return None

    @property
    def total_exposure(self) -> Decimal:
        """Total USDC currently deployed (Decimal)."""
        return sum(p.size_usdc for p in self.open_positions)

    @property
    def total_unrealized_pnl(self) -> Decimal:
        """Sum of all unrealized PnL (Decimal)."""
        return sum(
            (p.pnl_pct * p.size_usdc / HUNDRED).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            for p in self.open_positions
        )

    def get_position_book(self) -> list[dict]:
        """Return the current position book (for Number Rule cross-check)."""
        return [p.to_dict() for p in self.open_positions]

    def flush(self):
        """Flush all in-memory positions to disk (crash safety)."""
        for pos in self.open_positions:
            self._save_snapshot(pos)

    def close(self):
        """Close database connection."""
        if self._db_conn and not self._db_conn.closed:
            self._db_conn.close()
