# ENDGAME — Temporary Product Design (Waypoint)

> Last updated: 2026-10-03. This is NOT a final spec. It is a waypoint — an anchor to prevent drift during iterative build. Every future PR should reference this doc and note deviations.

## 1. Product Vision

**Single-purpose desktop application** that trades on Polymarket autonomously, with full human oversight via a dark-themed GUI. The system makes "serious predictions" using 4 strategy modules, tracks positions, manages risk, and provides live analytics. No web dashboard — everything lives in the Electron app.

## 2. Architecture (3 Components)

```
┌─────────────────────────────────────────────────────┐
│  poly-agent-app/          (Electron Desktop App)    │
│  ─────────────────────────                         │
│  • main.js          Electron entry point            │
│  • renderer/        Dark-theme UI (settings,        │
│                       strategy toggles, dashboard)   │
│  • agent/           Standalone agent process        │
│    ├── main.py     Agent lifecycle (start/stop)    │
│    ├── config.yaml Auth + limits + API keys        │
│    ├── core/       Operational resilience          │
│    │   ├── fuse_panel.py    Circuit breaker /      │
│    │   │                    retry / error log       │
│    │   └── heartbeat.py    Health monitor +        │
│    │                        message board            │
│    └── requirements.txt  Agent-only deps           │
│  • package.json     electron-builder NSIS target    │
└─────────────────────────────────────────────────────┘
           │ (agent communicates via) │
           ▼                            │
┌─────────────────────────────────────────────────────┐
│  poly-agent/            (Core Trading Engine)       │
│  ─────────────────────────                         │
│  • pyproject.toml     poly-agent>=0.2, fastapi,     │
│                        uvicorn, pydantic, aiohttp,  │
│                        pandas/numpy, rich, loguru,  │
│                        apscheduler                  │
│  • src/poly_agent/                            │
│    ├── engine.py          Master orchestrator      │
│    ├── risk_manager.py    Position sizing,         │
│    │                       stop-loss, exposure cap  │
│    ├── position_tracker.py Trade book, PnL calc    │
│    ├── main.py            CLI entry / startup       │
│    ├── execution/        Order execution layer     │
│    │   └── executor.py   Submit/cancel/preview     │
│    ├── strategies/       4 independent modules     │
│    │   ├── arbitrage.py   Cross-market arb         │
│    │   ├── edge_detection.py  Edge signal gen      │
│    │   ├── momentum.py    Trend-following signals  │
│    │   └── market_making.py  Bid/ask spread logic  │
│    ├── instrument_schema/ Market type definitions   │
│    │   ├── sports.py    Large (19 KB) — categories│
│    │   └── crypto.py    Crypto-specific types      │
│    ├── public_client/    Gateway to Polymarket US  │
│    │   └── gateway.py   HTTP client (requests)     │
│    ├── monitoring/       Live analytics            │
│    │   └── dashboard.py PnL chart, position list  │
│    └── analysis/         Research layer            │
│        └── news_sentiment.py News signal ingest    │
│  • requirements.txt      Minimal CLI deps           │
└─────────────────────────────────────────────────────┘
           │ (dev tooling) │
           ▼
┌─────────────────────────────────────────────────────┐
│  mcp-server/            (Dev Lifecycle Server)      │
│  ─────────────────────────                         │
│  • pyproject.toml     mcp, pydantic, sqlite-utils  │
│                        rich, requests, PyYAML       │
│  • src/mcp_server/                              │
│    ├── server.py          MCP tool definitions     │
│    ├── tools/dev_lifecycle/    Project state,      │
│    │   ├── project_state.py  phase tracking        │
│    │   └── experiment_log.py compare strategies    │
│    ├── tools/polymarket/     Live Polymarket ops   │
│    │   ├── market_scan.py   search/scan markets    │
│    │   ├── position_manager.py track positions     │
│    │   ├── order_tools.py   create/cancel orders   │
│    │   ├── portfolio_query.py  summary/balances    │
│    │   └── risk_dashboard.py    real-time risk     │
│    └── persistence/          Local state           │
│        ├── dev_state.py   SQLite (5 tables)        │
│        └── polymarket_cache.py JSON TTL cache      │
│  • tests/test_structure.py    Import-only check     │
└─────────────────────────────────────────────────────┘
```

## 3. Data Flow (Critical Path)

```
User sets params (UI) → Agent main.py reads config.yaml →
  Engine.run() polls market data via gateway →
  Strategies fire signals → Risk_manager sizes positions →
  position_tracker records → executor.submit() → Polymarket US API →
  heartbeat monitors health; fuse_panel catches errors & retries
```

### Constraints
- **Auth**: Polymarket US API requires auth tokens (stored in `agent/config.yaml`). No hardcoded credentials. No `polymarket-us` SDK JWT refresh logic exists yet.
- **Rate limits**: `polymarket-cache.py` has TTLs (market 300s, orderbook 60s, price 30s). Gateway must respect Polymarket's actual limits — unknown currently.
- **Risk**: `risk_manager.py` exists but its stop-loss/position-size logic is untested. **This is the single most critical file for real-money safety.**
- **Strategies**: 4 strategies fire independently. `engine.py` must coordinate them (no single strategy can dominate exposure without risk_manager approval).

## 4. Module Contracts (Interfaces)

### `engine.py` — `Engine.run()`
- Calls `gateway.scan_markets()` → passes to each strategy → collects signals → passes to `risk_manager.approve()` → calls `executor.submit()`
- Must handle: network errors (retry via fuse_panel), strategy timeouts, risk rejection
- **Must not** trade without `risk_manager.approve()` returning True

### `risk_manager.py` — `RiskManager.approve(position, market, strategy)`
- Returns `(bool, reason)` — must be explicit about rejection reasons
- Enforces: max exposure per strategy, max total exposure, stop-loss thresholds
- **Must not** be bypassed by any code path

### `position_tracker.py` — `PositionTracker.record_trade()` / `.get_positions()`
- Single source of truth for all open positions
- Must track: entry price, entry date, position size, strategy tag, stop-loss
- **Must not** lose data on crash — uses SQLite via `dev_state.db`? (No, uses in-memory `Dict` currently — **BUG** for a real-money system)

### `executor.py` — `OrderExecutor.submit(order)`
- Validates order params → calls gateway → records result → returns status
- Must handle: order fill partial fills, market moved, API error
- **Must not** silently swallow errors

### `gateway.py` — `PolymarketGateway`
- Thin HTTP wrapper over `polymarket-us` SDK or raw `requests` calls
- Must: rate-limit (configurable), log requests/responses, cache per `polymarket_cache.py`
- **Must not** expose API keys in logs

### `fuse_panel.py` — `FusePanel`
- Circuit breaker per dependency (gateway, executor, etc.)
- Must: open circuit after N failures, close after timeout, log every state change
- Must NOT cascade failures across unrelated dependencies

### `heartbeat.py` — `HeartbeatHarness`
- Periodic health check (every N seconds): gateway connectivity, position tracker sync, strategy health
- Message board: agent-to-agent task queue (for long-running research)
- Must: alert on failure (log to fuse_panel), self-heal where possible

## 5. Required Files (Non-Negotiable)

These MUST exist for the project to be buildable:

| File | Status | Notes |
|------|--------|-------|
| `poly-agent/src/poly_agent/__init__.py` | ✅ exists | bare `__version__ = "0.1.0"` |
| `poly-agent/src/poly_agent/strategies/__init__.py` | ⚠️ exists but empty | no `__all__` — importing by name will fail |
| `poly-agent/src/poly_agent/execution/__init__.py` | ??? | unknown |
| `poly-agent/src/poly_agent/instrument_schema/__init__.py` | ??? | unknown |
| `poly-agent/src/poly_agent/public_client/__init__.py` | ??? | unknown |
| `poly-agent/src/poly_agent/monitoring/__init__.py` | ??? | unknown |
| `poly-agent/src/poly_agent/analysis/__init__.py` | ??? | unknown |
| `poly-agent/src/poly_agent/strategies/arbitrage.py` | ✅ exists | 5.4 KB |
| `poly-agent/src/poly_agent/strategies/edge_detection.py` | ✅ exists | 6.3 KB |
| `poly-agent/src/poly_agent/strategies/momentum.py` | ✅ exists | 5.4 KB |
| `poly-agent/src/poly_agent/strategies/market_making.py` | ✅ exists | 4.0 KB |
| `poly-agent/src/poly_agent/execution/executor.py` | ✅ exists | 15.5 KB |
| `poly-agent/src/poly_agent/risk_manager.py` | ✅ exists | 5.1 KB |
| `poly-agent/src/poly_agent/engine.py` | ✅ exists | 6.1 KB |
| `poly-agent/src/poly_agent/main.py` | ✅ exists | 7.5 KB |
| `poly-agent/src/poly_agent/position_tracker.py` | ✅ exists | 7.7 KB |
| `poly-agent/src/poly_agent/monitoring/dashboard.py` | ✅ exists | 7.9 KB |
| `poly-agent/src/poly_agent/analysis/news_sentiment.py` | ✅ exists | 4.1 KB |
| `poly-agent/src/poly_agent/instrument_schema/sports.py` | ✅ exists | 19.1 KB |
| `poly-agent/src/poly_agent/instrument_schema/crypto.py` | ✅ exists | 3.4 KB |
| `poly-agent/src/poly_agent/public_client/gateway.py` | ✅ exists | 5.5 KB |
| `poly-agent-app/agent/main.py` | ✅ exists | 42.0 KB |
| `poly-agent-app/agent/core/fuse_panel.py` | ✅ exists | 18.6 KB |
| `poly-agent-app/agent/core/heartbeat.py` | ✅ exists | 16.5 KB |
| `poly-agent-app/agent/core/__init__.py` | ✅ exists | exports all |
| `poly-agent-app/agent/config.yaml` | ✅ exists | auth + limits |
| `poly-agent-app/agent/__init__.py` | ❌ MISSING | agent module has no `__init__.py` |
| `poly-agent-app/renderer/index.html` | ✅ exists | 287 lines dark UI |
| `poly-agent-app/renderer/styles.css` | ✅ exists | 727 lines dark theme |
| `poly-agent-app/renderer/app.js` | ✅ exists | 17.0 KB |
| `poly-agent-app/main.js` | ✅ exists | 5.7 KB |
| `poly-agent-app/package.json` | ✅ exists | electron-builder NSIS |
| `mcp-server/src/mcp_server/server.py` | ✅ exists | 10.6 KB |
| `mcp-server/src/mcp_server/persistence/dev_state.py` | ✅ exists | 11.0 KB |
| `mcp-server/src/mcp_server/persistence/polymarket_cache.py` | ✅ exists | 9.3 KB |
| `mcp-server/src/mcp_server/tools/dev_lifecycle/project_state.py` | ✅ exists | 3.8 KB |
| `mcp-server/src/mcp_server/tools/dev_lifecycle/experiment_log.py` | ✅ exists | 8.2 KB |
| `mcp-server/src/mcp_server/tools/polymarket/` | ??? | 5 tools (market_scan, position_manager, order_tools, portfolio_query, risk_dashboard) |
| `mcp-server/src/mcp_server/__init__.py` | ⚠️ exists but filename may be corrupted (non-ASCII chars) |

### Files That DO NOT Exist Yet
- `poly-agent-app/agent/__init__.py` — **must be created**
- `poly-agent/tests/` — **must be created** (no test directory)
- `pytest.ini` or `pyproject.toml[tool.pytest]` config — **must be created**
- `.gitignore` — **must be created** (secrets, `__pycache__`, `node_modules`, `*.db`)
- `README.md` at `poly-agent/` root — exists (6.5 KB), but could be tighter

## 6. Build Order (How to go from zero to running)

```
1. Create missing `__init__.py` files (poly-agent submodule packages)
2. `cd poly-agent && pip install -e .`  (install engine)
3. `cd mcp-server && pip install -e .`  (install MCP server)
4. `cd poly-agent-app && npm install`   (install deps)
5. `cd poly-agent-app && npm start`     (launch Electron app)
6. `cd mcp-server && python start.bat`  (start dev server)
```

### Prerequisites
- Python 3.12+ (verified: `python --version` works)
- Node.js 18+ (for Electron)
- Polymarket US account + API credentials (not in code)
- `polymarket-us>=0.2` pip package (referenced in `pyproject.toml` but not yet installed)

## 7. Drift Prevention Rules

1. **Every PR references ENDGAME.md** with `→ ENDGAME.md §N` noting which section it touches.
2. **No strategy can be added without a `risk_manager.approve()` code path** — the agent's core contract is `engine → strategies → risk_manager → executor`. Any bypass is a security bug.
3. **No new dependency without `pyproject.toml` update** — every `pip install` must be recorded.
4. **No `agent/config.yaml` changes without `config.yaml` schema validation** — auth tokens must never be in git. Use `.env` or vault.
5. **Position data persistence is non-optional** — `position_tracker.py` uses in-memory dict; this is a known bug. Any future version MUST use SQLite or file-backed storage.
6. **The ENDGAME.md itself is the single source of truth** — if it conflicts with a README, the README is stale. If it conflicts with code, the code is wrong (or the ENDGAME needs updating).

## 8. Key Documents (Read Before Coding)

| Doc | Path | Purpose |
|-----|------|---------|
| `ENDGAME.md` (you are here) | repo root | Product vision, architecture, drift rules |
| `API-ROUTING.md` | `Development/docs/API-ROUTING.md` | Every Polymarket endpoint, auth layer, timeout, rate limit, owner. **Update before adding any endpoint.** |
| `DATA-SAFETY.md` | `Development/docs/DATA-SAFETY.md` | The Number Rule. Six guarantees. State machine. **All money values, all position writes, all orders must pass these checks.** |
| `RESEARCH-GUIDE.md` | `Development/docs/RESEARCH-GUIDE.md` | Polymarket API docs (344 lines, read fully before auth work) |
| `BUILD-PLAN.md` | `Development/docs/BUILD-PLAN.md` | Phased build steps (already written, not reviewed here) |
| `PASS-02_DATA_MODELS.md` | `Development/docs/research-passes/PASS-02_DATA_MODELS.md` | Polymarket data model spec |
| `polymarket-docs-index.md` | repo root (~50 KB) | Index of scraped Polymarket docs |
| `poly-agent-docs-index.md` | repo root (~300 B) | Index of poly-agent docs |

## 9. Known Gaps (To Be Filled)

|| # | Gap | Priority |
|---|-----|----------|
| 1 | `position_tracker.py` in-memory dict — crashes on restart lose all positions | P0 (real money) |
| 2 | No tests for `risk_manager.py` | P0 |
| 3 | No tests for `engine.py` / strategy coordination | P0 |
| 4 | `executor.py` error handling is thin | P0 |
| 5 | `mcp-server/__init__.py` filename may contain non-ASCII chars (broken import) | P1 |
| 6 | Missing submodule `__init__.py` files (execution, instrument_schema, etc.) | P1 |
| 7 | `poly-agent-app/agent/__init__.py` missing | P1 |
| 8 | No `__all__` on strategy `__init__.py` | P2 |
| 9 | `polymarket-us` SDK docs not available (PDF exists but unprocessed) | P2 |
| 10 | No rate-limit implementation in gateway (depends on Polymarket docs) | P2 |
| 11 | `scrape_reference.py` missing — 96 scraped docs are orphaned HTML | P3 |
| 12 | No `.env` template or vault integration | P2 |

## 9. Endstate (What "Done" Looks Like)

- ✅ `pytest -x` passes (no import errors, no failures)
- ✅ `mcp-server/src/mcp_server/__init__.py` imports cleanly
- ✅ `poly-agent/src/poly_agent/__main__.py` starts and connects to gateway
- ✅ `poly-agent-app/` launches with working dark UI
- ✅ `agent/config.yaml` has auth but no secrets in git
- ✅ `position_tracker.py` persists to SQLite
- ✅ `risk_manager` has ≥10 tests covering approve/reject logic
- ✅ Strategy comparison via MCP `compare_strategies()` works end-to-end
- ✅ `ENDGAME.md` is up-to-date (last line: "This doc is accurate as of YYYY-MM-DD")

---

*This document is temporary. When the codebase matures (≥50 tests, ≥3 deployment iterations), replace this with a proper `ARCHITECTURE.md` at the repo root.*
