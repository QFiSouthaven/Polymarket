# PolyAgent — Master Architecture Blueprint & Build Plan

> **Purpose:** Single source of truth for the Polymarket trading agent. Prevents architecture drift by documenting what exists, what's planned, and what decisions are pending.
>
> **Last updated:** 2025-07-14
> **Status:** Phase 0 — Blueprint & Verification

---

## 1. Project Goal

**One sentence:** Make the number in my account go up, not down.

No fancy features. No research papers. Just a conservative trading agent that finds small edges and executes them with strict risk limits. Profitability is the only metric that matters.

### Non-Goals (Explicitly Out of Scope)
- Building a UI for end-users (the Electron app is internal dev tooling only)
- Creating new strategies beyond the 4 already implemented
- Automating KYC/funding workflows
- Any feature not directly tied to PnL

---

## 2. Architecture Overview — The Four API Layers

The Polymarket Exchange exposes four distinct API layers. Each maps to a component in our codebase:

```
┌─────────────────────────────────────────────────────────────┐
│                    POLYMARKET EXCHANGE                       │
│                     (polymarket.us)                          │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: Gamma API          → poly-agent/public_client/    │
│         Market data, order books, BBO                      │
│         Auth: None (public gateway)                        │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: CLOB API           → poly-agent/execution/        │
│         Order placement, position management               │
│         Auth: JWT (RSA key pair → Auth0)                   │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: Data API v2        → poly-agent/position_tracker/ │
│         Positions, PnL, portfolio                          │
│         Auth: JWT                                          │
├─────────────────────────────────────────────────────────────┤
│  Layer 4: Relayer API        → poly-agent/execution/        │
│         Gas management (on-chain settlement)               │
│         Auth: JWT + on-chain tx signing                    │
└─────────────────────────────────────────────────────────────┘
```

### Component Mapping

| Layer | Our Code | Status | Notes |
|-------|----------|--------|-------|
| Gamma API (market data) | `public_client/gateway.py` | ✅ Implemented | Unauthenticated, rate-limited |
| CLOB API (orders) | `execution/executor.py` | ✅ Implemented | JWT auth, order placement |
| Data API v2 (positions/PnL) | `position_tracker.py` | ⚠️ Partial | Needs verification against live API |
| Relayer API (gas) | `execution/executor.py` | ⚠️ Partial | Token manager exists; gas tx signing TBD |

---

## 3. Component Inventory — What Exists vs What's Missing

### ✅ VERIFIED EXISTING (confirmed by reading source)

#### Core Engine (`poly-agent/src/poly_agent/`)
| File | Purpose | Verified? |
|------|---------|-----------|
| `engine.py` | Strategy orchestrator, runs all strategies in parallel | ✅ Yes |
| `risk_manager.py` | Hard risk limits (kill switch, daily loss, profit target) | ✅ Yes |
| `position_tracker.py` | Tracks open positions and PnL | ⚠️ Partial — needs live API verification |
| `main.py` | Entry point / CLI | ⚠️ Needs review |

#### Strategies (`poly-agent/src/poly_agent/strategies/`)
| File | Purpose | Verified? |
|------|---------|-----------|
| `arbitrage.py` | Bundle arbitrage (lowest risk) | ✅ Yes — structure confirmed |
| `edge_detection.py` | Detects mispriced markets using sentiment + history | ✅ Yes |
| `momentum.py` | Follows price trends with volume filters | ✅ Yes |
| `market_making.py` | Places bid/ask spreads (disabled by default) | ✅ Yes |

#### Execution (`poly-agent/src/poly_agent/execution/`)
| File | Purpose | Verified? |
|------|---------|-----------|
| `executor.py` | JWT auth, order placement, position mgmt | ✅ Yes — TokenManager + CLOB client confirmed |

#### Public Client (`poly-agent/src/poly_agent/public_client/`)
| File | Purpose | Verified? |
|------|---------|-----------|
| `gateway.py` | Unauthenticated market data fetcher | ✅ Yes — base URLs for preprod/prod confirmed |

#### Analysis & Schemas
| File | Purpose | Verified? |
|------|---------|-----------|
| `analysis/news_sentiment.py` | News sentiment scoring for edge detection | ⚠️ Needs review |
| `instrument_schema/crypto.py` | Crypto market instrument definitions | ✅ Yes |
| `instrument_schema/sports.py` | Sports market instrument definitions | ✅ Yes |

#### Monitoring (`poly-agent/src/poly_agent/monitoring/`)
| File | Purpose | Verified? |
|------|---------|-----------|
| `dashboard.py` | Risk dashboard / health monitoring | ⚠️ Needs review |

#### Config
| File | Purpose | Status |
|------|---------|--------|
| `config.yaml` | Agent config (auth, capital, strategies, risk) | ✅ Structure verified — **needs real credentials** |

### 🟡 PARTIAL / NEEDS VERIFICATION

| Component | Gap | Priority |
|-----------|-----|----------|
| Preprod auth end-to-end | Never tested against live preprod API | 🔴 HIGH |
| Position tracker vs Data API v2 | Schema may have drifted from Polymarket docs | 🔴 HIGH |
| Relayer gas signing | Token manager exists; on-chain tx flow not verified | 🟡 MEDIUM |
| News sentiment pipeline | Exists but integration with edge_detection unclear | 🟡 MEDIUM |

### ❌ MISSING (Not Yet Built)

| Component | Why It's Needed | Priority |
|-----------|-----------------|----------|
| **Master blueprint** (this doc) | Prevents drift between components | ✅ DONE |
| Preprod verification script | Prove auth + market data work before any trading | 🔴 HIGH |
| Strategy comparison framework | Compare bundle arb vs edge detection on same markets | 🟡 MEDIUM |
| PnL tracking dashboard | Real-time profit/loss display (beyond risk_manager) | 🟢 LOW |

---

## 4. Phased Implementation Plan

### Phase 0: Blueprint & Verification (CURRENT — THIS PHASE)
**Goal:** Prove the foundation works before writing any new code.

| Step | Task | Success Criteria | Owner |
|------|------|-----------------|-------|
| 0.1 | Write this blueprint | ✅ DONE | Agent |
| 0.2 | Verify preprod auth works end-to-end | JWT refresh + market data fetch succeeds against `gateway.preprod.polymarketexchange.com` | User (with agent help) |
| 0.3 | Verify position tracker schema matches live Data API v2 | Position query returns valid data on preprod | Agent |
| 0.4 | Run bundle arb strategy in dry-run mode (no orders placed) | Strategy produces opportunities, no errors | Agent |

**Decision needed from user before Phase 1:**
- [ ] Budget allocation amount (config has $1000 default — is this correct?)
- [ ] Start with preprod or prod? (recommend: preprod first)
- [ ] Which strategy to prioritize first? (recommend: bundle arb — lowest risk, most mechanical)

### Phase 1: First Profitable Trade (Preprod)
**Goal:** Execute one real trade on preprod and verify PnL tracking works.

| Step | Task | Success Criteria |
|------|------|-----------------|
| 1.1 | Enable bundle arb in config, set `enabled: true` | Config updated |
| 1.2 | Run agent against preprod markets for 30 min | Finds opportunities, places orders |
| 1.3 | Verify order appears on preprod portfolio | Position visible in preprod UI/API |
| 1.4 | Close position and verify PnL calculation | Profit/loss matches expected |

### Phase 2: Edge Detection Strategy
**Goal:** Add the higher-edge strategy once bundle arb is proven.

| Step | Task | Success Criteria |
|------|------|-----------------|
| 2.1 | Review edge_detection.py logic against Polymarket docs | Logic verified, no API contract mismatches |
| 2.2 | Test news sentiment pipeline end-to-end | Sentiment scores correlate with market moves |
| 2.3 | Run in dry-run mode comparing to bundle arb | Edge detection finds different opportunities |

### Phase 3: Momentum Strategy (Optional)
**Goal:** Add trend-following for markets with clear directional bias.

| Step | Task | Success Criteria |
|------|------|-----------------|
| 3.1 | Review momentum.py against Polymarket docs | Logic verified |
| 3.2 | Test on high-volume sports/crypto markets | Finds valid trends, no false signals |

### Phase 4: Production Readiness (Only After Preprod Proven)
**Goal:** Move to production with confidence.

| Step | Task | Success Criteria |
|------|------|-----------------|
| 4.1 | Switch config `environment: prod` | Auth works against live API |
| 4.2 | Set real capital amount in config | Budget matches user's intent |
| 4.3 | Run for 7 days monitoring PnL | No unexpected losses, risk limits hold |

---

## 5. Risk Framework — Hard Limits (Non-Negotiable)

These are documented in `config.yaml` and enforced by `risk_manager.py`. They cannot be overridden by any strategy.

| Limit | Value | Enforcement |
|-------|-------|-------------|
| Max per trade | $50 USDC | Checked before every order placement |
| Daily loss limit | $100 USDC | Kill switch triggers if hit |
| Stop-loss per position | -20% | Auto-liquidate |
| Take-profit per position | +15% | Auto-close |
| Max open positions | 20 | Block new orders when reached |
| Consecutive losses (kill switch) | 5 in a row | Hard stop, requires manual reset |
| Portfolio drawdown limit | -15% | Hard stop, requires manual reset |
| Daily profit target | $50 USDC | Pause trading for the day |

### Risk Manager Logic Flow
```
can_trade() →
  1. Kill switch active? → NO (block everything)
  2. Daily loss >= limit? → NO (pause for day)
  3. Profit target hit? → YES (pause for day)
  4. Max positions reached? → YES (block new orders)
  5. Per-trade budget available? → YES (allow trade)
```

---

## 6. Decision Log — Pending User Input

These decisions block progress and require explicit user approval:

| # | Decision | Options | Recommendation | Status |
|---|----------|---------|----------------|--------|
| D1 | Budget allocation | $500 / $1000 / $2000 / other | Start with $500 (conservative) | ⏳ Pending |
| D2 | Environment to start | preprod vs prod | Preprod first, always | ⏳ Pending |
| D3 | First strategy | bundle arb / edge detection / momentum | Bundle arb (mechanical, lowest risk) | ⏳ Pending |
| D4 | Trading hours | 24/7 / business hours / custom | Business hours + overnight for crypto | ⏳ Pending |
| D5 | Scan frequency | 30s / 60s / 180s | 60s (balance between responsiveness and rate limits) | ⏳ Pending |

---

## 7. Verification Checklist — Before Any Trading

### Pre-Trade Checklist (run before Phase 1)
- [ ] `config.yaml` has correct environment (`preprod`)
- [ ] `auth.private_key_path` points to a valid RSA key file
- [ ] `auth.client_id` and `auth.audience` are filled in
- [ ] Preprod auth token refresh works (tested manually)
- [ ] Public gateway returns market data on preprod endpoint
- [ ] Position tracker schema matches live Data API v2 response
- [ ] Risk manager can_trade() logic verified with test values
- [ ] Bundle arb strategy produces opportunities in dry-run mode

### Pre-Production Checklist (run before Phase 4)
- [ ] All preprod tests passed for 7+ days
- [ ] PnL tracking matches actual portfolio changes
- [ ] Risk limits triggered correctly under stress testing
- [ ] Kill switch tested and verified
- [ ] User has reviewed and approved production budget amount

---

## 8. File Reference Map

### Core Files (always reference these)
| Path | Purpose |
|------|---------|
| `poly-agent/config.yaml` | **Single source of truth for all agent settings** |
| `poly-agent/src/poly_agent/engine.py` | Strategy orchestrator — the "brain" |
| `poly-agent/src/poly_agent/risk_manager.py` | Hard limits — cannot be overridden |
| `poly-agent/src/poly_agent/execution/executor.py` | JWT auth + order placement |
| `poly-agent/src/poly_agent/public_client/gateway.py` | Unauthenticated market data |

### Documentation (always reference these)
| Path | Purpose |
|------|---------|
| `polymarket-docs-index.md` | Complete Polymarket US docs (~300 pages linked) |
| `Development/docs/BUILD-PLAN.md` | **This document** — architecture blueprint |

### MCP Server (dev tooling)
| Path | Purpose |
|------|---------|
| `mcp-server/README.md` | Setup instructions for LM Studio integration |
| `mcp-server/src/mcp_server/tools/polymarket/` | Market scan, positions, orders, portfolio tools |

---

## 9. Anti-Drift Rules

These rules prevent the codebase from diverging from this blueprint:

1. **No new strategies without updating this doc.** Any new strategy must be documented in Section 3 (Component Inventory) and Section 4 (Phased Plan).
2. **API contract changes require doc updates.** If Polymarket's API changes, update `polymarket-docs-index.md` references AND the relevant component before code changes.
3. **Config is the single source of truth for settings.** Never hardcode limits in strategy files — always read from config.yaml via risk_manager.py.
4. **Preprod first, always.** No prod deployment without passing all preprod verification steps in Section 7.

---

## 10. Next Immediate Actions (After User Approval)

1. **User provides budget amount** → Update `config.yaml` capital section
2. **Agent writes preprod verification script** → Tests auth + market data end-to-end
3. **Agent runs bundle arb in dry-run mode** → Validates strategy logic without placing orders
4. **If all passes → Phase 1 begins** (first real trade on preprod)

---

*This document is the living blueprint for PolyAgent. Update it when architecture decisions change.*
