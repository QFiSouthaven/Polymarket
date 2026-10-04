# DATA SAFETY — The Number Rule (Holistic)

> **This is the highest-priority section of ENDGAME.md §3.** Every line here is a non-negotiable guard. Violating any rule is a P0 bug regardless of other considerations.
>
> Last updated: 2026-10-03 → ENDGAME.md §3 / API-ROUTING.md

## The Principle

> *"We do not trust a number until Polymarket's API has confirmed it matches what we sent, and we do not trust Polymarket's confirmation until we have checked it against our own persisted book."*

This means **three independent data sources must agree before any trade is "real"**:
1. What the agent calculated locally (the "intent")
2. What Polymarket's API acknowledged (the "receipt")
3. What the agent's persisted position book says (the "truth")

If any two disagree, **no trade executes**. Period.

## 1. The Number Rule — Six Guarantees

### Guarantee 1: No Floating-Point Money
```
❌ price = 0.1 + 0.2        # = 0.30000000000000004
❌ size_usdc = 50.5 / 2.1   # floating point division
✅ from decimal import Decimal
✅ price = Decimal('0.10')
✅ size_usdc = Decimal('50.50') / Decimal('2.10')
```

**Rule**: Every field in `Position`, `Opportunity`, `RiskState`, and API payloads that represents money, price, or quantity **must be `Decimal` or `int` (cents)**. `float` is forbidden in the trading data domain.

### Guarantee 2: Round-Trip Order Verification
```
agent sends:  {"market_slug": "abc", "side": "BUY", "price": 0.50, "quantity": 100}
    → Polymarket confirms: {"order_id": "xyz", "price": 0.50, "quantity": 100}
    → executor records:     {"order_id": "xyz", ...}
    → position_tracker:     adds position with quantity=100 (VERIFIED)
```

**Rule**: After `executor.submit()` returns success:
- `executor` must parse the API response and **assert** `confirmed.quantity == sent.quantity` (within 0.01 for rounding).
- If `confirmed.quantity != sent.quantity` → log error, **do not** add position. The order was partially filled; the agent must decide (retry, cancel remainder, accept partial).
- `position_tracker.add_position()` must **never** be called with unverified quantities.

### Guarantee 3: Position Book Is The Single Source of Truth
```
┌─────────────────────────────────────────────────────────┐
│ position_tracker.py                                     │
│ open_positions: list[Position]  ← THIS IS THE TRUTH    │
│ closed_positions: list[dict]    ← history              │
│ total_exposure: property       ← sum of open positions │
└─────────────────────────────────────────────────────────┘
```

**Rule**: `position_tracker.total_exposure` is the ONLY number used by `risk_manager.can_trade()` and `risk_manager.can_open_position()`. No other file may compute exposure independently. If `position_tracker` is wrong, **everything downstream is wrong**.

### Guarantee 4: Idempotency (No Double Orders)
```
agent → POST /v1/orders → network timeout → retry
    → Polymarket sees TWO orders (same market, same side, same price)
    → Agent thinks it has one; Polymarket has two
    → CATASTROPHIC: double exposure on one bet
```

**Rule**: Every `POST /v1/orders` call MUST include:
```python
headers["Idempotency-Key"] = f"{market_slug}:{side}:{price:.4f}:{size_usdc}:{iso_timestamp}"
```
If Polymarket returns the *same* `order_id` on retry → it was the same order (not a duplicate). If it returns a *different* ID → the first one landed, the second is a new one (potential bug — log and alert).

### Guarantee 5: Kill-Switch Is In The Executor, Not The Agent
```
❌ risk_manager.can_trade() → returns False → agent decides not to trade
   (agent could be overridden, bypassed, or the check could be skipped)

✅ executor.submit() → calls risk_manager.approve() INSIDE the submit method
   → Even if agent calls executor.execute() directly, the gate is enforced.
```

**Rule**: `executor.execute(opportunity)` must:
1. Call `risk_manager.can_open_position(opportunity.size_usdc)` — if False, **log and return error**.
2. Call `risk_manager.can_trade()` — if False, **log and return error**.
3. Only then build the API request body.

This means: **no code path in the entire project can bypass risk_manager**. The gate lives at the point of API call, not at the strategy level.

### Guarantee 6: Position Book Must Match Polymarket's Server State
```
Agent's open_positions: [ABC: BUY 100 @ 0.50, DEF: SELL 50 @ 0.30]
Polymarket's positions: [ABC: BUY 100 @ 0.50]  ← DEF was closed externally
```

**Rule**: On every `heartbeat.py` cycle:
1. Call `executor.get_portfolio()` → get Polymarket's server-side position list.
2. Compare against `position_tracker.open_positions`.
3. If mismatch → **ALERT, DO NOT TRADE** until the agent can reconcile.
4. Reconciliation: positions in tracker but not on server → cancel (or accept loss). Positions on server but not in tracker → add to tracker (was lost on crash).

This is the **most critical data safety check** for a real-money system.

## 2. The Data Safety Checklist (Every PR)

Before any commit that touches trading logic, verify:

| # | Check | How |
|---|-------|-----|
| 1 | No `float` in `Position`, `Opportunity`, `RiskState` fields | `grep -rn "float" poly-agent/src/poly_agent/*.py` |
| 2 | `executor.execute()` calls `risk_manager.can_trade()` before API call | Read `executor.py` lines ~110-130 |
| 3 | `executor.execute()` calls `risk_manager.can_open_position(size)` | Same |
| 4 | Idempotency key on every `POST /v1/orders` | `grep "Idempotency-Key" executor.py` |
| 5 | `position_tracker.total_exposure` is the *only* exposure calc | `grep "exposure" poly-agent/src/poly_agent/*.py` |
| 6 | No `position_tracker.add_position()` called without verified quantity | `grep "add_position" poly-agent/src/poly_agent/engine.py` |
| 7 | `heartbeat.py` calls `executor.get_portfolio()` and compares | Read `heartbeat.py` scan_cycle |
| 8 | `fuse_panel` is wired to `gateway.py` (circuit breaker) | `grep -rn "fuse_panel" gateway.py` |
| 9 | `polymarket_cache.py` TTLs are configurable per-endpoint | Read cache module |
| 10 | `agent/main.py` auth delegates to `executor.TokenManager` | Read agent/main.py auth section |

## 3. Data Integrity Violations (What To Do)

### P0: Position book ≠ Polymarket server state
- **Action**: Freeze all trading. Alert human via UI. Log everything.
- **Never**: Auto-correct and trade. You cannot trust your book if it doesn't match the server.

### P1: Idempotency key collision (same key, different order_id)
- **Action**: Log error, cancel the new order, retry with new key. Alert.
- **Never**: Accept both orders.

### P2: Partial fill (quantity differs from requested)
- **Action**: Log partial fill amount. Add position with *confirmed* quantity. Notify user.
- **Never**: Add position with requested (wrong) quantity.

### P3: 401/403 on auth
- **Action**: Invalidate cached token, refresh, retry once. If still failing → FAIL, alert, shutdown trading.
- **Never**: Retry indefinitely (you could be using a stale/revoked key).

### P4: 429 rate limit
- **Action**: Wait (backoff), retry. If repeated → open circuit breaker, alert, pause trading.
- **Never**: Ignore 429 and keep hammering.

## 4. Persistence Rules

### position_tracker.py (currently in-memory — P0 bug)
The current `open_positions: list[Position] = []` is **in-memory only**. On crash, restart, or power loss: **all positions are lost**. The agent would place "duplicate" positions on top of Polymarket's server positions (which it can't see because its book was wiped).

**Required fix before any real money**:
- Add SQLite persistence to `position_tracker.py` (or use `dev_state.db` from MCP server).
- On init: load positions from DB. On every trade: write to DB. On heartbeat: verify against Polymarket.
- DB schema must include: `position_id`, `market_slug`, `side`, `entry_price`, `size_usdc`, `entry_time`, `strategy`, `status`.
- **This is non-negotiable for real money.** No "later" — before a single bet is placed.

### polymarket_cache.py (JSON TTL cache)
- Current: JSON file, written on every change. If process crashes during write → corrupt file.
- **Fix**: Write to temp file, rename (atomic swap). Or use SQLite with WAL mode.
- TTLs: currently hardcoded (300s, 60s, 30s). Make configurable per-endpoint.

## 5. The Three-State Machine

For every trade:
```
    CREATED ────[executor.submit OK]───► ACKNOWLEDGED ────[Polymarket confirms]───► FILLED
       │                                    │                                         │
       │  [executor.error]                │ [heartbeat: book ≠ server]              │
       ▼                                    ▼                                         ▼
    FAILED                              ALERT (freeze)                        CLOSED (PnL recorded)
```

- **CREATED**: Agent calculated the trade, risk_manager approved it, API request sent.
- **ACKNOWLEDGED**: Polymarket returned `order_id`. Agent has the receipt. Position not yet added to tracker.
- **FILLED**: Position confirmed on server. Added to `position_tracker`. Heartbeat will verify.
- **FAILED**: API error, risk rejection, or 401. No position added. Agent can retry or abandon.
- **ALERT (freeze)**: Book mismatch. Trading is PAUSED until human confirms reconciliation.

This state machine **must be enforced in code**. No "trust the agent knows the state." Every state transition is logged and verifiable.

## 6. Endstate for Data Safety

When this section is complete:
- ✅ Every monetary value is `Decimal` or `int` (no `float` in trading domain)
- ✅ `executor.execute()` gates on `risk_manager` (hard-coded, un-bypassable)
- ✅ Idempotency key on every order POST
- ✅ `position_tracker` persists to SQLite (survives crash)
- ✅ `heartbeat.py` compares local book vs Polymarket server (on every cycle)
- ✅ `fuse_panel` wired to `gateway.py` (circuit breaker on API failures)
- ✅ `polymarket_cache.py` uses atomic file writes (no corruption)
- ✅ `agent/main.py` auth delegates to `executor.TokenManager` (one auth source)
- ✅ State machine (CREATED→ACKNOWLEDGED→FILLED→CLOSED) enforced in code
- ✅ `api_routing.md` is the source of truth for all endpoints (no ad-hoc URLs)
