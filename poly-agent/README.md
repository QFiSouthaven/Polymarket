# 🤖 PolyAgent — Autonomous Polymarket Exchange Trading Agent

**Platform**: [Polymarket Exchange](https://polymarket.us) (institutional-grade prediction market)  
**Docs**: https://docs.polymarket.us/llms.txt  

---

## How It Works

```
┌─────────────────────────────────────────────────┐
│  YOU: Flip enabled:true in config.yaml          │
│       Run: python -m poly_agent.main            │
├─────────────────────────────────────────────────┤
│  AGENT WAKES UP → Scans markets every 30s      │
│    ├── Bundle Arbitrage (guaranteed profit)     │
│    ├── Edge Detection (find mispriced markets)  │
│    ├── Momentum (ride trends)                   │
│    └── Market Making (capture spreads)          │
├─────────────────────────────────────────────────┤
│  FINDS OPPORTUNITY → Risk check → Execute trade │
│  Monitors positions → Auto-cashout at +15%      │
│  Cuts losses at -20%                            │
│  Stops if daily loss limit hit                  │
├─────────────────────────────────────────────────┤
│  LIVE DASHBOARD: http://localhost:8080          │
│    See PnL, positions, activity in real-time    │
│    Hit STOP button to kill everything           │
└─────────────────────────────────────────────────┘
```

## Quick Start

### 1. Install Dependencies
```bash
cd F:/PolyMarket/poly-agent
pip install -r requirements.txt
```

### 2. Onboard with Polymarket Exchange (One-Time)
Visit https://docs.polymarket.us/trader-guide/authentication for full onboarding:
- Generate RSA key pair → submit public key to `onboarding@polymarket.us`
- Receive your **Client ID** and **Audience** values
- Fund account via wire transfer

### 3. Configure (REQUIRED)
Edit `config.yaml`:
```yaml
auth:
  environment: "preprod"        # ← START HERE! Pre-prod has TEST FUNDS
  client_id: "your-client-id"   # From onboarding
  audience: "https://api.preprod.polymarketexchange.com"
  private_key_path: "/path/to/your/private_key.pem"

agent:
  enabled: true                 # ← FLIP THIS TO START
```

### 4. Start the Agent
```bash
python -m poly_agent.main
```

The agent will scan markets, find edges, place bets automatically, and show a live dashboard at `http://localhost:8080`.

## Strategies

| Strategy | How It Works | Risk Level |
|----------|-------------|------------|
| **Bundle Arbitrage** | Buys YES+NO when sum < $1.00 → guaranteed profit | 🟢 Low (near-risk-free) |
| **Edge Detection** | Compares PolyMarket price vs external truth sources | 🟡 Medium |
| **Momentum** | Rides price trends in active markets | 🟡 Medium |
| **Market Making** | Captures bid-ask spreads on liquid markets | 🟢 Low |

## Risk Management (Hard Limits)

| Limit | Default | What It Does |
|-------|---------|-------------|
| Per-trade max | $50 USDC | Never bets more than this on one market |
| Daily loss limit | -$100 USDC | Stops trading for the day if hit |
| Stop loss | -20% per position | Auto-liquidates losing positions |
| Take profit | +15% per position | Auto-cashouts winning positions |
| Kill switch | 5 consecutive losses OR 15% drawdown | Emergency full stop |

## Polymarket Exchange Specifics

### Environments (use preprod first!)
| Environment | REST API | gRPC | Auth Domain |
|-------------|----------|------|-------------|
| **Pre-production** | `api.preprod.polymarketexchange.com` | `grpc-api.preprod.polymarketexchange.com:443` | `pmx-preprod.us.auth0.com` |
| **Production** | `api.polymarket.us` | `grpc-api.prod.polymarketexchange.com:443` | `pmx-prod.us.auth0.com` |

### Authentication Flow
1. Generate RSA key pair → submit public key to Polymarket
2. Sign JWT with private key (RS256) → exchange for access token via Auth0
3. Token refreshes every 150 seconds automatically
4. Include `Bearer <token>` in all API requests

### Instrument Identification (IMPORTANT)
**Never parse slugs.** Use strongly-typed schemas:
- **Sports**: Match on `market_sport_type` enum (e.g., `football_team_full_game_winner`)
- **Crypto**: Match on `crypto_market_type` enum (`updown`, `strike`, `range`, `hit`)

### Rate Limits
- REST API: ~60 requests/minute
- gRPC streaming: 100 messages/sec ingress, max 20 concurrent streams
- FIX protocol: 150 messages/sec per session (institutional only)

## File Structure

```
poly-agent/
├── config.yaml              ← YOU EDIT THIS (enabled, keys, limits)
├── requirements.txt         ← pip install -r requirements.txt
├── README.md               ← This file
└── src/poly_agent/
    ├── main.py             ← The "brain" — orchestrates everything
    ├── engine.py           ← Strategy runner & trade executor
    ├── risk_manager.py     ← Hard limits (cannot be overridden)
    ├── position_tracker.py ← Position management + auto-cashout
    ├── public_client/      ← Polymarket Exchange public gateway client
    │   └── gateway.py      ← Fetch markets, books, BBO without auth
    ├── instrument_schema/  ← Typed market identification (no slug parsing!)
    │   ├── sports.py       ← Sports schema parser
    │   └── crypto.py       ← Crypto price schema parser
    ├── strategies/         ← 4 independent strategy modules
    ├── execution/          ← Polymarket Exchange REST + WebSocket client
    │   └── executor.py     ← JWT auth, order placement, portfolio queries
    └── monitoring/         ← Live web dashboard (FastAPI)
        └── dashboard.py    ← Real-time PnL, positions, STOP button
```

## ⚠️ Important Notes

- **Start in pre-production** — it has test funds so you can verify everything works before risking real money
- **Bundle arbitrage is the most reliable strategy** — near-risk-free when prices are mispriced
- **Edge detection needs external data sources** (news APIs, polling data) for best results
- **This is real money in production** — start small ($50-100) and monitor closely
