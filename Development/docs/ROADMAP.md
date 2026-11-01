# Roadmap & Iteration Log

**Owner:** every contributor · **Updated in:** every PR · **Supersedes:** `ENDGAME.md` §9 gap table where they disagree

This is the only place that records *where the build actually stands*. Design intent lives in
[ENDGAME.md](../../ENDGAME.md), sequencing lives in [BUILD-PLAN.md](BUILD-PLAN.md); this file records
measured state, blockers and what happened last iteration. Every claim below was executed on the
machine, not copied from a doc — re-measure it when you touch it.

---

## 1. Where we are

**Phase 0 — Blueprint & Verification** ([BUILD-PLAN.md §4](BUILD-PLAN.md)). The skeleton installs and
imports; no strategy has produced an edge verified against real external data, so no capital is at risk.

| Gate | Status | Evidence (measured 2026-11-01) |
|------|--------|--------------------------------|
| `pip install -e ./poly-agent` | ✅ works | `Would install poly-agent-0.2.0`; full dependency set resolves |
| `pip install -e ./mcp-server` | ✅ works | `Would install polyagent-mcp-server-0.1.0` |
| Engine imports cleanly | ⚠️ partial | package exports fixed, but never exercised end-to-end (`engine.py` untested) |
| `pytest` in `poly-agent/` | ❌ empty | **0 tests collected** — `tests/test_risk_manager.py` is a 1-line placeholder |
| `pytest` in `mcp-server/` | ❌ red | **4 passed, 2 failed** (`test_server_module`, `test_codebase_scan`) |
| Electron app launches | ⬜ unverified | not run this iteration |
| Position persistence | ❌ missing | in-memory dict (B-3) |
| Real-money safety gate | ❌ unproven | `risk_manager` has zero tests (B-4) |

## 2. Blockers

Ordered by what blocks real money. Each row is a unit of work: one blocker per branch/PR.

| ID | Blocker | Why it matters | Status / next action |
|----|---------|----------------|--------------------|
| **B-1** | Invalid build backend `setuptools.backends._legacy:_Backend` in both `pyproject.toml` files | Steps 2–3 of the ENDGAME §6 build order were impossible: `BackendUnavailable: Cannot import 'setuptools.backends._legacy'` | ✅ **Closed 2026-11-01** — switched to `setuptools.build_meta`, verified both packages install |
| **B-2** | `polymarket-us>=0.2` admits unverified drift (PyPI latest is **2.4.1**) and the SDK surface was never checked against our client code | Every gateway call, auth flow and order payload depends on that surface; ENDGAME §9 gap 9 says the SDK docs are still unprocessed | ⬜ Open — read the 2.4.1 API, then pin `polymarket-us~=2.4` and reconcile `public_client/gateway.py` |
| **B-3** | `position_tracker.py` keeps the book in an in-memory dict | A crash or restart silently loses every open position in a real-money system (ENDGAME §9 gap 1) | ⬜ Open — SQLite-backed store; add a kill-restart round-trip test |
| **B-4** | No tests for `risk_manager.py` / `engine.py`; `tests/test_risk_manager.py` is empty | The risk gate is the only thing between a bug and lost capital. ENDGAME §9 endstate wants ≥ 10 approve/reject tests | ⬜ Open — write the suite first, in `poly-agent/tests/`, marked `risk` |
| **B-5** | `mcp-server` suite red: `TypeError: FastMCP.__init__…` and `scan_codebase_status()` looking for `mcp-server/src/poly-agent/src` | A red suite hides new regressions; the path bug is a hard-coded relative assumption about the repo layout | ⬜ Open — pin the `mcp` version that matches our call, derive paths from the repo root |
| **B-6** | Dependency manifests disagree: `requirements.txt` lists `requests`, `PyJWT[crypto]`, `cryptography`; `pyproject.toml` does not | Two sources of truth → an environment built from one cannot import code written against the other | ⬜ Open — make `pyproject.toml` authoritative, reduce `requirements.txt` to a lockfile or delete it |
| **B-7** | Strategies emit signals from placeholder data: `_sports_edge_estimate()`/`_crypto_edge_estimate()` return `None`, momentum falls back to `random.uniform(...)`, news sentiment counts keywords + noise | Trading on random noise is worse than not trading (AGENT-AGENDA §2.6, §III pillar 1) | ⬜ Open — no data source ⇒ no signal; replace fallbacks with BRTI/odds/news feeds |

## 3. Backlog mapped to BUILD-PLAN phases

| BUILD-PLAN phase | Work items here | Blockers cleared first |
|---|---|---|
| **Phase 0** (now) | Repo scaffolding, CI green, test harness for `risk_manager`, dependency reconciliation | B-1 ✅, B-4, B-5, B-6 |
| **Phase 1** — first preprod trade | Position persistence, executor error handling, gateway rate limits, restart-resume | B-2, B-3 |
| **Phase 2** — edge detection | Real crypto/sports reference prices, derived confidence instead of heuristics | B-7 |
| **Phase 3** — momentum | Real price-history endpoint behind `_get_price_history()` | B-7 |
| **Phase 4** — production readiness | Kill-switch drills, 10k-hour drift checks, deployment iterations | all above |

## 4. Doc drift to reconcile

- `ENDGAME.md` §8 lists `poly-agent-docs-index.md` at the repo root; that file does not exist.
- `ENDGAME.md` has two sections numbered **9** (Known Gaps and Endstate).
- Per-package READMEs predate the build fix in B-1; re-check their install instructions.

## 5. Iteration log

| Date | Iteration | Outcome | Next |
|------|-----------|---------|------|
| 2026-11-01 | Repo structuring: git hygiene, logical commits of the outstanding `__init__`/dashboard work, build-backend fix, README + CONTRIBUTING + CI + issue/PR templates, stale worktree pruned | B-1 closed; baseline measured (engine tests 0 collected, MCP suite 4/2); working tree clean on `main` | B-4: write the `risk_manager` approve/reject suite |
