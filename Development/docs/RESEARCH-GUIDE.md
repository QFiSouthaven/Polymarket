# Polymarket US — Research Guide for Trading Agent Development

> **Purpose:** Single reference document covering all API contracts, data structures, and constraints relevant to building the PolyAgent trading system.
>
> **Last updated:** 2026-10-02
> **Source:** https://docs.polymarket.us (official docs) + SDK v2.1.0 source code

---

## 1. Architecture Overview — Four API Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    POLYMARKET EXCHANGE                       │
│                     (polymarket.us)                          │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: Public Gateway       → gateway.polymarket.us      │
│         Market data, order books, BBO, events               │
│         Auth: None (public)                                │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: Authenticated API    → api.polymarket.us          │
│         Orders, portfolio, account balances                 │
│         Auth: Ed25519 signatures (X-PM-* headers)          │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: gRPC Streaming       → grpc-api.prod.polymarketexchange.com:443 │
│         Real-time market data, order updates, RFQ events   │
│         Auth: JWT Bearer token (M2M OAuth)                 │
├─────────────────────────────────────────────────────────────┤
│  Layer 4: WebSocket Streams    → wss://api.polymarket.us/v1/ws/... │
│         Private WS: order, position, balance updates       │
│         Markets WS: order book + trade streaming           │
│         Auth: JWT Bearer token                             │
└─────────────────────────────────────────────────────────────┘
```

### Preprod Environment (NOT YET MIGRATED)
| Endpoint | URL | Status |
|----------|-----|--------|
| Public Gateway | `gateway.preprod.polymarketexchange.com` | ❌ DNS not resolving |
| Auth API | `api.preprod.polymarketexchange.com` | ⚠️ Requires JWT/Bearer (not Ed25519) |
| gRPC Streaming | `grpc-api.preprod.polymarketexchange.com:443` | TBD |

**Critical Finding:** Preprod has NOT been migrated to the new Ed25519 auth system. It still requires JWT Bearer tokens via OAuth client credentials flow. Our Ed25519 key works on production only.

---

## 2. Authentication

### Production (Ed25519 — SDK v2.1.0)
```python
from polymarket_us import PolymarketUS

client = PolymarketUS(
    key_id="YOUR_KEY_ID",           # UUID string
    secret_key="YOUR_SECRET_KEY",   # Base64-encoded Ed25519 private key (64 bytes)
    api_base_url="https://api.polymarket.us",  # default
    gateway_base_url="https://gateway.polymarket.us",  # default
)
```

**Signing process (SDK internals):**
1. Message = `timestamp_ms + HTTP_METHOD + path`
2. Decode secret_key from base64 → if 64 bytes, take first 32 (seed)
3. Sign message with Ed25519
4. Attach headers: `X-PM-Access-Key`, `X-PM-Timestamp`, `X-PM-Signature`
5. Timestamp must be within **30 seconds** of server time

### Preprod (JWT/Bearer — NOT YET SUPPORTED BY SDK)
Requires OAuth client credentials flow to Auth0 tenant (`pmx-preprod.us.auth0.com`). Our Ed25519 key is NOT registered there yet.

---

## 3. Data Hierarchy — Events → Markets → Instruments

```
Category (e.g., Sports, Crypto)
  └── Subcategory (e.g., NFL, NBA)
        └── Series (e.g., "NFL 2025-26 Season")
              └── Event (e.g., "Chiefs vs Eagles — Feb 9, 2026")
                    └── Product (template: AEC/ATC/ASC/TSC)
                          └── Instrument(s) (tradable outcomes)
```

### Products = Trading Types
| Code | Type | Example Slug | Description |
|------|------|-------------|-------------|
| **AEC** | Moneyline | `aec-nfl-kc-phi-2026-02-09` | Who wins? (binary) |
| **ATC** | 3-way outcome | `atc-mls-atl-clt-2026-03-22-draw` | Win/Draw/Lose |
| **ASC** | Point spread | `asc-nfl-hou-mia-2025-12-16-pos-4pt5` | Spread betting |
| **TSC** | Totals (O/U) | `tsc-nfl-ne-den-2026-01-25-47-5` | Over/under score |

### Instrument Naming Convention
```
{product_code}-{event_id}-{strike/outcome}
```
Examples:
- `aec-cbb-char-hamp-2026-02-26` — College basketball moneyline
- `atc-mls-atl-clt-2026-03-22-draw` — MLS 3-way, draw outcome
- `asc-nfl-hou-mia-2025-12-16-pos-4pt5` — NFL spread +4.5
- `tsc-nfl-ne-den-2026-01-25-47-5` — NFL total over 47.5

### Crypto Price Markets (different structure)
```
Series: btc-strike-daily
  └── Event: btc-above-day-2026-09-21 (expires 5:00 PM ET)
        ├── Market: $73,500 or above
        ├── Market: $74,000 or above
        └── Market: $74,500 or above
```

### Key Instrument Metadata Fields
| Field | Use |
|-------|-----|
| `price_scale` | Price multiplier (usually ×100; $0.60 = 60) |
| `tick_size` | Minimum price increment (usually 0.01) |
| `minimumTradeQty` | Smallest valid quantity (contracts) |
| `orderPriceMinTickSize` | Smallest valid price increment |
| `start_date` / `expiration_date` | Trading window |
| `settlement_price_logic` | How market resolves |

---

## 4. Trading Interface — Orders API

### Order Types
| Type | Description | Use Case |
|------|-------------|----------|
| `ORDER_TYPE_LIMIT` | Limit order at specified price | Most strategies |
| `ORDER_TYPE_MARKET` | Market order at best available price | Quick execution |

### Order Intents (Direction)
| Intent | Meaning | Price Reference |
|--------|---------|-----------------|
| `ORDER_INTENT_BUY_LONG` | Buy YES contracts | `price.value` = YES price |
| `ORDER_INTENT_SELL_LONG` | Sell YES (close long) | `price.value` = YES price |
| `ORDER_INTENT_BUY_SHORT` | Buy NO contracts | `price.value` = 1.00 - NO_price |
| `ORDER_INTENT_SELL_SHORT` | Sell NO (close short) | `price.value` = 1.00 - NO_price |

**⚠️ Critical Rule:** `price.value` ALWAYS represents the YES side price, regardless of intent. To trade NO at price X: set `price.value = 1.00 - X`.

### Time in Force
| Value | Description | Notes |
|-------|-------------|-------|
| `TIME_IN_FORCE_DAY` | Expires end of trading day | ⚠️ Does NOT auto-cancel at 5pm during trade rolls — use GTD instead |
| `TIME_IN_FORCE_GOOD_TILL_CANCEL` | Active until filled/cancelled | Default for most strategies |
| `TIME_IN_FORCE_GOOD_TILL_DATE` | Expires at specific time | Use with `goodTillTime` field |
| `TIME_IN_FORCE_IMMEDIATE_OR_CANCEL` | Fill what's available, cancel rest | For aggressive fills |
| `TIME_IN_FORCE_FILL_OR_KILL` | Must fill entirely or cancel | For full execution guarantee |

### Order Validation Rules
- Price must be between **0.01 and 0.99** (absolute exchange limits)
- Quantity must align with market's `minimumTradeQty`
- Price must align with market's `orderPriceMinTickSize`
- Invalid orders receive an orderID but are rejected by the exchange

### Slippage Tolerance (Market Orders)
```json
{
  "slippageTolerance": {
    "currentPrice": {"value": "0.50", "currency": "USD"},
    "ticks": 5
  }
}
```
- `ticks`: max price ticks away from reference (takes priority over bips)
- Default for market orders: **unlimited** (no protection!)

### Order States
| State | Code | Meaning |
|-------|------|---------|
| `ORDER_STATE_PENDING_NEW` | 7 | Received, not yet processed |
| `ORDER_STATE_NEW` | 0 | Resting on the book |
| `ORDER_STATE_REPLACED` | 4 | Cancel-replace via modify |
| `ORDER_STATE_REJECTED` | 5 | Rejected by exchange |
| `ORDER_STATE_EXPIRED` | 6 | GTD expired |

### Manual Order Indicator (Required)
- `MANUAL_ORDER_INDICATOR_MANUAL` — human-placed
- `MANUAL_ORDER_INDICATOR_AUTOMATIC` — **your agent MUST use this**

---

## 5. Portfolio & Positions API

### Position Fields (use Decimal versions, not int64)
| Field | Type | Description |
|-------|------|-------------|
| `netPositionDecimal` | string(decimal) | Net position (positive=long, negative=short) |
| `qtyBoughtDecimal` | string(decimal) | Total quantity bought |
| `qtySoldDecimal` | string(decimal) | Total quantity sold |
| `qtyAvailableDecimal` | string(decimal) | Available to trade |
| `cost` | Amount | Cost basis |
| `realized` | Amount | Realized PnL (closed positions) |
| `cashValue` | Amount | Current unrealized value |
| `marketMetadata.slug` | string | Market identifier |

### Account Balances
| Field | Description |
|-------|-------------|
| `currentBalance` | Available cash |
| `buyingPower` | Capital available for trading (after margin) |
| `assetNotional` | Total notional value of securities |
| `openOrders` | Value tied up in open orders |
| `marginRequirement` | Required margin for positions |

### Activities (Trade History)
- `ACTIVITY_TYPE_TRADE` — trade execution details
- `ACTIVITY_TYPE_POSITION_RESOLUTION` — market settlement
- `ACTIVITY_TYPE_ACCOUNT_WITHDRAWAL` — withdrawal
- `ACTIVITY_TYPE_TRANSFER` — transfer between accounts

---

## 6. Real-Time Data — Streaming

### WebSocket (SDK-supported)
| Endpoint | Purpose | Auth Required |
|----------|---------|---------------|
| `wss://api.polymarket.us/v1/ws/private` | Order, position, balance updates | ✅ Yes |
| `wss://api.polymarket.us/v1/ws/markets` | Order book + trade streaming | ❌ No (public) |

### gRPC Streaming (Advanced)
| Service | Purpose | Endpoint |
|---------|---------|----------|
| `MarketDataSubscriptionAPI.CreateMarketDataSubscription` | Real-time market data | `grpc-api.prod.polymarketexchange.com:443` |
| `OrderEntryAPI.CreateOrderSubscription` | Order execution reports | Same endpoint |
| `RFQAPI.StreamRFQEvents` | Combo RFQ lifecycle events | Same endpoint |

### Rate Limits (gRPC)
- Max concurrent streams per firm: **20**
- Ingress message rate: **100 msg/sec** across all streams (averaged over 1 min)
- Egress (server→client): unlimited

---

## 7. Candlestick Data (OHLCV)

### Method 1: Pre-Aggregated REST (Recommended)
```python
# Server-side aggregation, configurable intervals
candles = client.markets.candlesticks(slug, interval="5m")  # 1m, 5m, 15m, 1h, 4h, 1d
```

### Method 2: Manual Aggregation from Trades
- Query individual trades → group by interval → calc O/H/L/C/V client-side
- More flexible but higher latency

### Real-Time Candle Builder (SDK)
```python
builder = RealtimeCandleBuilder(interval_seconds=300)  # 5-min candles
for market_update in stream:
    builder.on_trade(price=market_update.last_px, volume=market_update.last_qty, timestamp=...)
```

---

## 8. Strategy-Relevant Data Points

### For Bundle Arbitrage
- Order book depth (L2 data) on each leg of a bundle
- Settlement price logic per instrument
- Cross-market correlations
- Price_scale and tick_size per instrument

### For Edge Detection
- Historical settlement accuracy vs. market prices
- News sentiment scores → expected price movement
- Volume trends (rising volume + direction = momentum signal)
- Time decay (approaching expiration increases volatility)

### For Momentum
- Candlestick patterns (5m, 1h, 4h intervals)
- Volume profile across time windows
- Order book imbalance (bid/ask ratio)
- Trade flow aggressor analysis (`isAggressor` flag in activities)

### For Market Making
- BBO spread width
- Order book depth at each level
- Fill rate / execution latency
- Inventory risk (position concentration)

---

## 9. Known Issues & Gotchas

| Issue | Impact | Workaround |
|-------|--------|------------|
| Preprod not migrated to Ed25519 | Can't test auth on preprod with current key | Use production or request preprod creds from Polymarket |
| DAY orders don't auto-cancel at 5pm | Orders linger past intended expiry | Use GTD with explicit timestamp |
| `price.value` always = YES side price | Easy to make pricing errors when trading NO | Always compute: `NO_price → price.value = 1.00 - X` |
| Market order slippage default = unlimited | Can get terrible fills in thin markets | Always set `slippageTolerance` for market orders |
| Deprecated int64 fields on positions | May lose precision | Use `*Decimal` fields exclusively |
| Preprod gateway DNS not resolving | Can't reach preprod public API | Use production gateway (public data is shared) |

---

## 10. Agent Configuration Mapping

| Blueprint Setting | Polymarket US Equivalent | Notes |
|------------------|-------------------------|-------|
| `max_per_trade_usdc` | `quantity` × `price.value` per order | Must respect `minimumTradeQty` |
| `stop_loss_pct: -0.20` | Monitor `cashValue` vs `cost` on positions | Auto-liquidate when PnL < -20% |
| `take_profit_pct: 0.15` | Same monitoring approach | Auto-close when PnL > +15% |
| `max_open_positions: 20` | Count active positions via `portfolio.positions()` | Block new orders at limit |
| `kill_switch.consecutive_losses: 5` | Track realized PnL per trade in activities | Hard stop after N losses |

---

## 11. Quick Reference — Common Operations

```python
# Fetch markets
markets = client.markets.list({"limit": 50, "active": True})

# Get order book + BBO
book = client.markets.book("aec-nfl-kc-phi-2026-02-09")
bbo = client.markets.bbo("aec-nfl-kc-phi-2026-02-09")

# Place a limit order (BUY YES at $0.55)
order = client.orders.create({
    "marketSlug": "aec-nfl-kc-phi-2026-02-09",
    "type": "ORDER_TYPE_LIMIT",
    "price": {"value": "0.55", "currency": "USD"},
    "quantity": 10,
    "tif": "TIME_IN_FORCE_GOOD_TILL_CANCEL",
    "intent": "ORDER_INTENT_BUY_LONG",
    "manualOrderIndicator": "MANUAL_ORDER_INDICATOR_AUTOMATIC"
})

# Check positions + PnL
positions = client.portfolio.positions()
balances = client.account.balances()

# Cancel all orders
client.orders.cancel_all()

# Close a specific position
client.orders.close_position({"marketSlug": "...", "quantity": 10})
```

---

*This guide is the living reference for PolyAgent development. Update when Polymarket API changes.*
