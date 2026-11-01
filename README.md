# PolyMarket — Autonomous Prediction-Market Trading Agent

A single-purpose desktop application that trades on Polymarket autonomously, with full human
oversight through a dark-themed Electron GUI. Four strategy modules emit signals, a risk manager
gates every order, and the position book is the single source of truth for PnL.

> **Status: Phase 0 — blueprint & verification.** The engine skeleton runs, but no strategy has yet
> been proven against real market data. This system is **not** trading-ready. See
> [Development/docs/BUILD-PLAN.md](Development/docs/BUILD-PLAN.md) §4 for the phase plan and
> [Development/docs/ROADMAP.md](Development/docs/ROADMAP.md) for the live backlog of blockers.

---

## Repository map

| Path | What it is | Language |
|------|------------|----------|
| [`poly-agent/`](poly-agent/) | Core trading engine: `engine.py` → strategies → `risk_manager.py` → `execution/executor.py`, plus position tracking, monitoring and market-type schemas. | Python ≥ 3.10 |
| [`poly-agent-app/`](poly-agent-app/) | Electron desktop app (dark UI) that owns the agent lifecycle; `agent/core/fuse_panel.py` (circuit breaker) and `agent/core/heartbeat.py` (health monitor). | JS + Python |
| [`mcp-server/`](mcp-server/) | Dev-lifecycle MCP server: project state, experiment log, live Polymarket tools, SQLite dev state, TTL cache. | Python ≥ 3.11 |
| [`Development/docs/`](Development/docs/) | The governing documents (see below) plus research passes. | Markdown |
| [`Development/polymarket_docs/`](Development/polymarket_docs/) | ~96 scraped Polymarket API reference pages (**git-ignored**, regenerable). | HTML |
| [`.firewall/`](.firewall/) | Windows scripts that block SMB/Docker-bridge traffic for the sandboxed agent. | .bat / .ps1 |
| `player -clean-/` | Superseded App2–App6 experiments. Kept on disk, **git-ignored** and out of the mainline. | Python |

## Read these before writing code

| Order | Document | Why it matters |
|-------|----------|----------------|
| 1 | [ENDGAME.md](ENDGAME.md) | Product vision, architecture, module contracts, drift rules. **The single source of truth.** |
| 2 | [Development/docs/BUILD-PLAN.md](Development/docs/BUILD-PLAN.md) | Phased build plan (Phase 0 → 4), risk limits, verification checklists. |
| 3 | [Development/docs/AGENT-AGENDA.md](Development/docs/AGENT-AGENDA.md) | Honest per-strategy assessment and the definition of "winning". |
| 4 | [Development/docs/DATA-SAFETY.md](Development/docs/DATA-SAFETY.md) | The Number Rule — applies to every money value, position write and order. |
| 5 | [Development/docs/API-ROUTING.md](Development/docs/API-ROUTING.md) | Endpoint map with auth layer, timeout and rate limit. **Update before adding an endpoint.** |
| 6 | [Development/docs/RESEARCH-GUIDE.md](Development/docs/RESEARCH-GUIDE.md) | Polymarket API research (read fully before any auth work). |
| — | [Development/docs/ROADMAP.md](Development/docs/ROADMAP.md) | Live backlog, blockers and iteration log. **Update in every PR.** |

## Quickstart

```bash
# 0. Prerequisites: Python >= 3.11 (engine requires >=3.10, MCP server >=3.11), Node.js >= 18
python -m venv .venv && source .venv/Scripts/activate     # Windows Git-Bash

# 1. Core engine
python -m pip install -e ./poly-agent

# 2. Dev-lifecycle MCP server
python -m pip install -e "./mcp-server[dev]"

# 3. Desktop app
cd poly-agent-app && npm install && npm start
```

Credentials: copy [`.env.example`](.env.example) to `.env` and fill it in. `config.yaml` files are
git-ignored on purpose — **no secret ever goes into git** (see [SECURITY.md](SECURITY.md)).

## Tests

```bash
cd poly-agent  && python -m pytest tests -q                    # engine + risk suite
cd mcp-server  && python -m pytest tests -q                    # structure/import checks
cd poly-agent  && python -m pytest tests -m risk               # risk_manager hard limits only
cd poly-agent  && python -m pytest tests -m "not slow and not strategy"
```

Current baseline (measured, not aspirational — details in
[Development/docs/ROADMAP.md](Development/docs/ROADMAP.md)): `poly-agent` collects **0** tests
(`tests/test_risk_manager.py` is a placeholder), `mcp-server` runs **4 passed / 2 failed**.

## Conventions

Work happens on short-lived branches (optionally in git worktrees under `.worktrees/`, which are
git-ignored) that merge into `main`. Every commit and PR references the section of `ENDGAME.md` it
touches. Full rules, checklists and the anti-drift gates: [CONTRIBUTING.md](CONTRIBUTING.md).

## Known gaps

The P0 list (position book is in-memory, no risk-manager tests, strategies emit on placeholder or
random data) is tracked as blockers **B-1 … B-7** in
[Development/docs/ROADMAP.md](Development/docs/ROADMAP.md), which supersedes the stale gap table in
ENDGAME.md §9 wherever the two disagree.
