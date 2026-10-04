# Agent Agenda — Poly-Agent Trading System

**Status**: Draft | **Last updated**: 2026-10-03 | **Author**: Agent
**Reference**: See `ENDGAME.md` for architecture, `DATA-SAFETY.md` for the Number Rule, `API-ROUTING.md` for endpoint map.

> This document is the Agent's operational intent. It defines what "winning" means, the current state of truth (not hope), and the design philosophy for the prediction layer. Every future PR must reference it.

---

## I. What "Winning" Means

The Agent does not "win" by finding the most edges. It wins by **compounding real money without losing it to bugs, drift, or overconfidence**. Three hard constraints:

1. **No single trade can materially reduce total portfolio value** — `risk_manager` is the gate, not a suggestion.
2. **No strategy can degrade another's output** — the 4-strategy parallel scan must be independent and non-collusive.
3. **The system must survive 10,000 hours of operation without a silent drift** — positions, edge estimates, or routing that diverge from intent are unacceptable.

---

## II. Current State (Truth, Not Hope)

The codebase is a skeleton with placeholder meat. Below is the honest assessment of each strategy as written.

### 2.1 Bundle Arbitrage (`strategies/arbitrage.py`)

| Aspect | Status |
|--------|--------|
| **Edge math** | ✅ Correct (YES + NO < $1.00 → guaranteed profit if prices are real) |
| **Reverse arb** | ✅ Correct (YES + NO > $1.00 → sell both sides) |
| **Edge estimate** | `edge = (1.0 - bundle_sum) / bundle_sum * 100` — mathematically exact |
| **Confidence** | `min(0.95, edge * 2)` — heuristic, not derived from data |
| **Sizing** | `min(max_position_usdc, remaining_budget * 0.3)` — fixed 30% of budget, not Kelly |
| **Coverage** | First 200 markets per cycle — arbitrary cutoff |
| **Order book parsing** | String matching `side.lower() in str(a).lower()` — fragile, not schema-based |
| **Verdict** | **Real edge, real math. Deployable with minor improvements.** |

### 2.2 Edge Detection (`strategies/edge_detection.py`)

| Aspect | Status |
|--------|--------|
| **Sports edge** | `_sports_edge_estimate()` → returns `None` (line 109: "Placeholder") |
| **Crypto edge** | `_crypto_edge_estimate()` → returns `None` (line 120: "For now, returns None") |
| **External data** | `polymarket-us` SDK referenced but never imported; BRTI/CF Benchmarks not wired |
| **Confidence** | `min(0.9, edge * 3)` — heuristic on a computed edge that is always `None` |
| **Sizing** | `min(max_per_trade * 0.5, max_per_trade * edge * 10)` — uses edge which is always `None` → falls through |
| **Verdict** | **Dead code path. No edge is ever produced. Must be replaced with real data sources before any deployment.** |

### 2.3 Momentum (`strategies/momentum.py`)

| Aspect | Status |
|--------|--------|
| **Price history** | `_get_price_history()` fallback: `import random; return [base * (1 + random.uniform(-0.02, 0.02)) for _ in range(6)]` |
| **Edge math** | Linear regression slope normalized — mathematically correct for real data |
| **Volume filter** | `min_volume_24h = config.get("min_volume_24h", 1000)` — reasonable threshold |
| **Confidence** | `min(0.85, abs(momentum_score) * 5)` — heuristic |
| **Sizing** | `min(max_per_trade * 0.7, volume_24h / 100)` — volume-based, not Kelly |
| **Verdict** | **Trades on random noise in fallback. Must replace `_get_price_history` with real Polymarket price history endpoint or Polymarket SDK before any deployment.** |

### 2.4 Market Making (`strategies/market_making.py`)

| Aspect | Status |
|--------|--------|
| **Spread logic** | Correct: `best_bid` < `best_ask`, spread > threshold → place limit orders |
| **Order placement** | Bid at `best_bid + spread * 0.3`, ask at `best_ask - spread * 0.3` — reasonable |
| **Inventory management** | ❌ None. No cross-market hedging, no stale-quote detection |
| **Liquidity check** | Only checks `spread_pct > min_spread_pct` — does not verify order book depth |
| **Verdict** | **Mechanically correct but incomplete. Missing depth check, stale-quote detection, and inventory risk.** |

### 2.5 News Sentiment (`analysis/news_sentiment.py`)

| Aspect | Status |
|--------|--------|
| **Method** | Keyword counting: `"win" + "pass" + "approve" + "confirm" + "declare"` minus `"lose" + "fail" + "reject" + "cancel" + "drop"` |
| **Probability** | `0.5 + score * 0.05 + random.uniform(-0.1, 0.1)` — random noise dominates |
| **Confidence** | Always `0.3` (line 60: "Low confidence without real data source") |
| **Historical accuracy** | In-memory dict, no persistence, no update mechanism |
| **Verdict** | **Garbage in, garbage out. Must be replaced with real LLM sentiment analysis on news headlines before any deployment.** |

### 2.6 Strategy Summary

| Strategy | Real Edge? | Deployable? | Priority to Fix |
|----------|-----------|-------------|----------------|
| Bundle Arb | ✅ | ⚠️ Minor | **P0** — real edge, real money |
| Edge Detection | ❌ | ❌ | **P0** — dead code path |
| Momentum | ❌ (fallback is random) | ❌ | **P0** — random noise |
| Market Making | ⚠️ Partial | ⚠️ Missing depth | **P1** |
| News Sentiment | ❌ | ❌ | **P0** — garbage output |

---

## III. Prediction Layer — Design Philosophy

> "sophisticated, reiterated and enhanced until it's bulletproof beyond just self-improving without any degradation towards efficiency, Accuracy, and Consistency."

### Three Pillars (in order of priority)

**1. Accuracy (hard constraint on everything else)**

Every edge estimate must be grounded in real external data. No random fallbacks, no keyword counting on titles, no unverified "true probability." If the data source is unavailable, the strategy must **not produce a signal**. Better to miss an edge than to act on a fake one.

The Number Rule applies here: every edge estimate is three-source verified (PM price, external source A, external source B). If two sources disagree on the edge direction, no trade executes.

**2. Efficiency (hard constraint on improvement)**

Self-improvement cannot add latency that makes the agent slower than Polymarket's own market-making bots. The 4-strategy parallel scan (30s timeout each) is the upper bound. Any new strategy must fit within this budget. No strategy can become a sequential bottleneck. The `scan_all_strategies()` `asyncio.gather` pattern is correct; no strategy can block another.

**3. Consistency (hard constraint on self-improvement)**

The improvement loop must not degrade. Every new version of a strategy must pass all the same acceptance criteria as the previous version, plus the new ones. There is no "it's better on average" — it must be better on every test case. This is the "beyond self-improving" guarantee: the agent must not optimize for one metric (edge) at the cost of another (latency, false-positive rate, drawdown).

### The "Beyond Self-Improving" Guarantee

The agent does not "self-improve" by tweaking parameters until it looks better. It improves by:

1. **Adding verified external data sources** (BRTI, odds APIs, news sentiment APIs)
2. **Adding independent signal channels** (one new data source per edge estimate, never replacing an existing one without parallel testing)
3. **Rejecting improvements that increase variance without reducing mean error**

This is the bulletproofing: the system can only get better by adding *independent* information, never by optimizing a single metric at the expense of correctness.

---

## IV. Operational Intent

### 4.1 Ingest Real External Truth

The agent needs real data sources wired in. The `polymarket-docs-index.md` has the endpoints; `RESEARCH-GUIDE.md` has the auth model. Specifically:

- **Crypto**: BRTI (CF Benchmarks) for BTC/ETH reference prices. The `CryptoSchemaParser` already identifies the market family (`strike`, `range`, `hit`, `updown`) and horizon (`5m`, `15m`, `1h`, `4h`, `weekly`, `monthly`). The `_crypto_edge_estimate()` method must compare Polymarket price against BRTI price.
- **Sports**: Odds APIs (DraftKings, BetMGM, etc.) for historical and live odds comparison. The `SportsSchemaParser` has 71+ market types mapped. The `_sports_edge_estimate()` method must compare Polymarket price against odds-api consensus.
- **News**: Real LLM-powered sentiment on news headlines. The `NewsSentimentAnalyzer.estimate_probability()` must fetch headlines via API → run LLM analysis → return probability. No keyword counting. No random noise.

### 4.2 Detect Real Edges

Each strategy must produce a **verified** edge with a **derived** confidence score (not hardcoded heuristics). Every edge must be traceable to its data sources.

### 4.3 Size and Risk

Every order must pass the Number Rule three-source check (intent ↔ API receipt ↔ persisted book). Kelly criterion with proper variance estimation, not fixed percentages. The risk_manager gate must be enforced at the executor layer, not just at strategy emission.

### 4.4 Execute and Verify

- Idempotent POST to `/v1/orders` with order-idempotency-key
- Heartbeat book reconciliation (local book vs Polymarket server)
- Partial-fill handling (track confirmed quantity, not just "order sent")
- Circuit breaker (fuse_panel already exists in `poly-agent-app/agent/core/fuse_panel.py` — must be wired to executor)

### 4.5 Learn Without Drifting

- Track every trade's outcome vs prediction
- Update edge estimates only when new independent data is added
- Never update estimates in a way that increases variance without reducing mean error
- Every update must pass the consistency test (new version passes all old acceptance criteria + new ones)

---

## V. What the Agent Needs (Not the Codebase)

The codebase has the skeleton. The Agent needs:

1. **Real data sources wired up** (BRTI for crypto, odds API for sports, news sentiment API) — the `polymarket-docs-index.md` has the endpoints.
2. **A real external truth pipeline** — this is the edge-generation engine, not the schema parser.
3. **Tests that prove the edge estimates are real** (not random, not None) — before a single real dollar is deployed.
4. **The Number Rule enforced at the executor layer** (three-source verification on every order, not just "risk_manager approves").
5. **Position persistence** (SQLite with WAL, not in-memory dict) — before any real money.

---

## VI. Success Criteria (Agent Wins When)

- [ ] All 5 strategies produce edges from **real data only** (no random, no None, no keyword counting)
- [ ] Every edge passes three-source verification before execution
- [ ] The parallel scan completes in ≤30s total
- [ ] No single trade can materially reduce portfolio value
- [ ] The system survives 10,000 hours without silent drift
- [ ] Every new strategy version passes all prior acceptance criteria
- [ ] Position book matches Polymarket server (heartbeat reconciliation)
- [ ] No order is sent without idempotency key and risk_manager approval

---

## VII. Known Gaps (Cross-Reference to ENDGAME.md)

| # | Gap | Priority |
|---|-----|----------|
| 1 | `position_tracker.py` in-memory dict — crashes lose all positions | P0 (real money) |
| 2 | Edge Detection `_sports_edge_estimate()` → `None` | P0 (dead code) |
| 3 | Edge Detection `_crypto_edge_estimate()` → `None` | P0 (dead code) |
| 4 | Momentum `_get_price_history()` → random fallback | P0 (random noise) |
| 5 | News Sentiment → keyword counting + random noise | P0 (garbage output) |
| 6 | Bundle Arb confidence is heuristic, not data-derived | P1 |
| 7 | No order book depth check in Market Making | P1 |
| 8 | No cross-market hedging in Market Making | P1 |
| 9 | `executor.py` no idempotency key on POST | P1 |
| 10 | No heartbeat book reconciliation wired | P1 |

---

*This document is a waypoint. It will be revised as the system matures. Every future PR must note deviations here.*
