# PolyAgent MCP Server — Persistent Memory for Dev Lifecycle & Polymarket App

A **Model Context Protocol (MCP) server** optimized specifically for:

1. **The PolyAgent Development Lifecycle** — experiment tracking, strategy comparison, codebase status monitoring
2. **The Actual Polymarket Application** — market scanning, position management, order tools, portfolio queries

## Architecture

```
mcp-server/
├── src/mcp_server/
│   ├── server.py              # MCP server entry point (tool definitions)
│   ├── persistence/
│   │   ├── dev_state.py       # SQLite: experiment logs, project state, codebase status
│   │   └── polymarket_cache.py  # JSON cache: markets, positions, prices with TTL
│   └── tools/
│       ├── dev_lifecycle/
│       │   ├── project_state.py    # get/set project state, scan codebase
│       │   └── experiment_log.py   # log/update/list experiments, compare strategies
│       └── polymarket/
│           ├── market_scan.py      # scan_markets, search_markets, get_market_detail
│           ├── position_manager.py # get_positions, close_position, partial_close
│           ├── risk_dashboard.py   # get_risk_state, check_can_trade, get_risk_alerts
│           ├── order_tools.py      # create_order, cancel_order, preview_order
│           └── portfolio_query.py  # get_portfolio_summary, get_account_balances, get_activities
├── pyproject.toml
└── dev_state.db               # SQLite database (created on first run)
```

## Installation

```bash
cd F:/PolyMarket/mcp-server/
pip install -e .
```

## Configuration in LM Studio / Bionic

Add to your `settings.json` or MCP configuration:

```json
{
  "mcpServers": {
    "polyagent-mcp-server": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "F:/PolyMarket/mcp-server/src"
    }
  }
}
```

Or use the `uv run` approach:

```json
{
  "mcpServers": {
    "polyagent-mcp-server": {
      "command": "uv",
      "args": ["run", "-p", "F:/PolyMarket/mcp-server/", "--", "python", "-m", "mcp_server.server"],
      "cwd": "F:/PolyMarket/mcp-server/src"
    }
  }
}
```

## Available Tools

### Dev Lifecycle Tools

| Tool | Description |
|------|-------------|
| `get_project_state(key)` | Get project metadata (phase, active strategy, etc.) |
| `set_project_state(key, value)` | Set project metadata |
| `scan_codebase_status()` | Scan poly-agent/src/ for module completion status |
| `log_experiment(name, strategy, ...)` | Log a new experiment run |
| `update_experiment(id, status, results)` | Update an existing experiment |
| `list_experiments(status_filter)` | Browse all logged experiments |
| `delete_experiment(id)` | Remove an experiment entry |
| `compare_strategies(exp_a, exp_b, ...)` | Side-by-side strategy comparison |

### Polymarket App Tools

| Tool | Description |
|------|-------------|
| `scan_markets(limit, category, min_volume)` | Browse active markets with filters |
| `get_market_detail(slug)` | Full market info + order book + BBO |
| `search_markets(query, limit)` | Keyword search across events/markets |
| `get_positions(market_slug)` | List all open positions (optionally filtered) |
| `close_position(position_id/market_slug)` | Close a position or all in a market |
| `partial_close_position(id/slug, pct)` | Cash out percentage of a position |
| `get_risk_state()` | Current risk state (budget, PnL, kill switch) |
| `check_can_trade(size_usdc)` | Check if trading is allowed right now |
| `create_order(slug, side, price, size)` | Place a new limit/market order |
| `cancel_order(order_id)` | Cancel a specific open order |
| `cancel_all_orders(market_slug)` | Cancel all orders (optionally filtered) |
| `preview_order(slug, side, price, size)` | Validate parameters + expected fills before submit |
| `get_portfolio_summary()` | Full portfolio overview (positions + balances) |
| `get_account_balances()` | Current balance and buying power |
| `get_activities(limit)` | Recent trading history |

### Utility Tools

| Tool | Description |
|------|-------------|
| `cache_stats()` | Polymarket cache statistics |
| `clear_cache()` | Clear all cached data |

## Persistence Layer

- **Dev State (SQLite)**: Experiment logs, project state key-values, codebase status, deployment history — stored in `dev_state.db` alongside the server. Survives restarts.
- **Polymarket Cache (JSON)**: Market snapshots, order books, prices with TTL-based expiration. Stored in `cache/polymarket_cache.json`. Reduces API calls and provides consistency across tool invocations.

## Dependencies on PolyAgent

This MCP server reuses the existing code from `poly-agent/src/`:
- `PublicGatewayClient` — unauthenticated market data (gateway.polymarket.us)
- `PolymarketExecutor` — authenticated order execution + portfolio queries
- `RiskManager` — hard risk limits and kill switch logic
- `PositionTracker` — position management with auto-cashout

## Development Notes

- The server uses `mcp.server.fastmcp.FastMCP` as the framework
- All tools are synchronous (run in event loop via `asyncio.get_event_loop().run_until_complete()`)
- Polymarket API calls go through preprod by default; set `environment: "prod"` in config.yaml for live trading
- Rate limits: 60 REST requests/minute, respect the `rate_limits` section in config.yaml
