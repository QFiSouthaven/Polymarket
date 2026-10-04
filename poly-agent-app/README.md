# 🤖 PolyAgent - Autonomous Polymarket Trading Agent

A desktop application that scans Polymarket Exchange for profitable opportunities and trades automatically. You just flip a switch — the agent does the rest.

## What It Does

- **Scans markets** every 30 seconds for arbitrage, edge detection, momentum, and market-making opportunities
- **Places trades** when it finds edges above your threshold
- **Manages positions** with auto cashout at take-profit (+15%) or stop-loss (-20%)
- **Tracks daily budget** — stops trading if you hit your loss limit
- **Chat interface** — type commands like "scan NFL" or "set budget $50"

## Quick Start (3 Steps)

### Step 1: Install Python Dependencies

Open a terminal in this folder and run:

```bash
cd agent
pip install -r requirements.txt
```

This installs `requests`, `pyjwt[crypto]`, `cryptography`, `rich` — everything the agent needs.

### Step 2: Configure Your Polymarket Credentials

Edit `agent/config.yaml`:

```yaml
auth:
  client_id: "YOUR_CLIENT_ID"          # From onboarding@polymarket.us
  audience: "https://api.prod.polymarketexchange.com"
  rsa_key_path: ""                     # Path to your RSA private key (from Polymarket)
```

> **Where do I get these?** When you signed up for the Polymarket Exchange API, they sent an email with your client ID and a downloadable RSA private key. Put that key file path here.

### Step 3: Install App & Run

```bash
npm install          # Installs Electron (the desktop app shell)
npm start            # Opens PolyAgent!
```

That's it — the app opens, you sign in, set your budget sliders, and click **Enable Agent**.

## How to Use It

| Action | Where |
|--------|-------|
| **Start/Stop agent** | Options menu → Enable Agent (or ⏹ button in chat) |
| **Set budget** | Left sidebar → Harness Settings → drag sliders |
| **Scan markets** | Chat panel: type "scan NFL" or click 🔍 Scan |
| **Auto-trade a market** | Click the AUTO button on any team row |
| **View positions** | Right panel → Current tab |
| **Stop agent** | Chat ⏹ Stop button or Options → Disable Agent |

## Strategies (toggle in Settings)

| Strategy | What it does |
|----------|-------------|
| **Arbitrage** | Finds mispriced bundles where sum of outcomes ≠ 1.0 (near-risk-free) |
| **Edge Detection** | Compares PolyMarket price vs external data for value edges |
| **Momentum** | Buys markets trending up, sells those trending down |
| **Market Making** | Places limit orders on both sides to capture spread |

## Risk Management (Hard Limits — Cannot Be Overridden)

- **Per-trade max**: $20 (configurable in Settings)
- **Daily loss limit**: -$50 (agent stops trading if hit)
- **Stop-loss**: -20% per position (auto-cashout)
- **Take-profit**: +15% per position (auto-cashout)

## Architecture

```
┌─────────────────────────────────────┐
│  Electron App Shell (main.js)       │  ← Desktop window, menu bar
│  ├── Chat Panel (renderer/)        │     Creates the UI you see
│  ├── Settings / Budget sliders      │     Handles auth, settings persistence
│  └── Spawns Python agent process   │     Manages lifecycle
├─────────────────────────────────────┤
│  Python Agent (agent/main.py)       │  ← The trading brain
│  ├── PolymarketClient              │     All API calls to Polymarket Exchange
│  ├── Strategies (arb/edge/mom/mm)  │     Detects opportunities
│  ├── RiskManager                   │     Hard limits, auto-cashout
│  └── Main Loop                     │     Scans every 30s
├─────────────────────────────────────┤
│  Polymarket Exchange API            │  ← External service
│  https://api.prod.polymarketexchange.com
└─────────────────────────────────────┘
```

## Troubleshooting

**"Agent won't start"** → Check `agent/config.yaml` has your client_id and audience. The RSA key path must point to an actual file.

**"Auth failed"** → Your JWT token may have expired. Restart the app (it auto-refreshes every 150s).

**"No markets found"** → You might be on preprod. Change `retail_api_base` in config.yaml to the production URL.

**Python not found** → Make sure Python is installed and in your PATH. Run `python --version` to check.

## Files

| File | Purpose |
|------|---------|
| `main.js` | Electron app shell (window, menu, spawns agent) |
| `renderer/index.html` | Main UI layout (chat, settings, teams) |
| `renderer/styles.css` | Dark theme styling |
| `renderer/app.js` | Frontend logic (chat, buttons, settings) |
| `agent/main.py` | Python trading agent (scans, trades, manages risk) |
| `agent/config.yaml` | Settings (budget, strategies, auth) |
| `agent/requirements.txt` | Python dependencies |

---

**Built for prompt-driven development.** No coding needed — just configure and run. 🚀
