# MCP Server — Design Contract
> See: `Development/docs/DATA-SAFETY.md`, `Development/docs/ENDGAME.md` (§3)

## 1. Product

Dev-lifecycle MCP — scans PolyAgent codebase, logs experiments, tracks state, queries Polymarket market/portfolio/risk data. **Not a trading executor**; trading logic lives in `poly-agent`'s `PolymarketExecutor`/`RiskManager`, MCP delegates there.

## 2. Six-Guarantee Map

All six apply because `order_tools.py` and `position_manager.py` route authenticated calls through `poly-agent`'s `PolymarketExecutor` and `position_tracker`. MCP delegates guards to the executor layer.

| # | Guarantee | Relevant? | How enforced |
|---|-----------|-----------|--------------|
| 1 | No Floating-Point Money | ✓ | `executor.py` converts all `price`/`size_usdc` to `Decimal` before API payloads; MCP passes floats → executor. |
| 2 | Round-Trip Order Verification | ✓ | `executor.submit()` parses API response, **asserts** `confirmed.quantity == sent.quantity` before `position_tracker.add_position()`; MCP `create_order`/`close_position` go through this path. |
| 3 | Position Book Is The Single Source of Truth | ✓ | `position_tracker.total_exposure` is the only exposure calc; `position_manager`/`risk_dashboard` query it, never compute independently. |
| 4 | Idempotency (No Double Orders) | ✓ | Every `executor.submit()` POST `/v1/orders` includes `Idempotency-Key` from `(market, side, price, size, ts)`; MCP `cancel_all_orders` uses same path. |
| 5 | Kill-Switch Is In The Executor, Not The Agent | ✓ | `executor.execute()` calls `risk_manager.can_open_position(size)` then `can_trade()` **inside** submit — no code path bypasses it; `risk_dashboard` only reads state. |
| 6 | Position Book Must Match Server State | ✓ | `heartbeat.py` calls `executor.get_portfolio()` → compares against `position_tracker.open_positions`; mismatch = ALERT + freeze; MCP `get_positions` reflects this cycle. |

**Note:** MCP is a dev tool. `order_tools.py`/`position_manager.py` call `poly_agent.execution.executor.PolymarketExecutor` (poly-agent package) which embeds the Number Rule. MCP never implements its own guard logic — it delegates. The three-state machine (CREATED→ACKNOWLEDGED→FILLED→FAILED→ALERT) is enforced in `poly-agent/engine.py`.

## 3. MCP Tool Contracts (grouped by module; 23 actual functions)

| Group | Tool (function) | Key Params | Guarantees Touched |
|-------|----------------|-----------|-------------------|
| **market_scan** | `scan_markets` | `limit, category, min_volume_24h, closed` | — |
| | `get_market_detail` | `market_slug` | — |
| | `search_markets` | `query, limit, category` | — |
| **position_manager** | `get_positions` | `market_slug` | #3 |
| | `close_position` | `market_slug, side` | #2, #3 |
| | `partial_close_position` | `market_slug, side, pct` | #2, #3, #6 |
| **order_tools** | `create_order` | `market_slug, side, price, size_usdc, type` | #1, #2, #4, #5 |
| | `cancel_order` | `order_id` | #4 |
| | `cancel_all_orders` | `market_slug` | #4 |
| | `preview_order` | `market_slug, side, price, size_usdc, type` | #1, #5 |
| **portfolio_query** | `get_portfolio_summary` | — | #3, #6 |
| | `get_account_balances` | — | — |
| | `get_activities` | `limit, market_slug` | — |
| **risk_dashboard** | `get_risk_state` | — | #5, #6 |
| | `check_can_trade` | — | #5 |
| **dev_lifecycle/project_state** | `get_project_state` | `key` | — |
| | `set_project_state` | `key, value` | — |
| | `scan_codebase_status` | — | — |
| **dev_lifecycle/experiment_log** | `log_experiment` | `name, strategy, description, parameters` | — |
| | `update_experiment` | `experiment_id, status, results` | — |
| | `list_experiments` | `strategy, limit` | — |
| | `delete_experiment` | `experiment_id` | — |
| | `compare_strategies` | `eid_1, eid_2` | — |

All tools use `DevStateDB` (SQLite) for persistence; `polymarket_cache.py` (JSON TTL) for market/position caching.
