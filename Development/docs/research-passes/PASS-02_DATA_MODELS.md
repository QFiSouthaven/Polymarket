# Research Pass 2: Data Models — Events, Markets, Instruments & Products

**Session ID:** PASS-02  
**Date:** 2026-10-02  
**Author:** PolyAgent Agent (this session)  
**Sources Consulted:**
- https://docs.polymarket.us/concepts/events-and-markets
- https://docs.polymarket.us/api-reference/market/overview
- `polymarket data guide/3-Data Structure/docs.polymarket.us-Naming Conventions.pdf`
- `polymarket data guide/3-Data Structure/docs.polymarket.us-Reference Data.pdf`
- `polymarket data guide/3-Data Structure/docs.polymarket.us-Asset Master.pdf`

---

## 1. Hierarchy — Five Levels Deep

```
Category (Sports, Politics, Crypto, Culture)
  └── Subcategory (NFL, NBA, MLS, etc.)
        └── Series (e.g., "NFL 2025-26 Season")
              └── Event (e.g., "nfl-ne-den-2026-01-25")
                    └── Product (AEC/ATC/ASC/TSC) — template applied to event
                          └── Instrument(s) — specific tradable outcomes
```

**Uniqueness Rules:**
| Level | Scope | Example |
|-------|-------|---------|
| Category + Subcategory | Globally unique | `nfl` = NFL subcategory |
| Product | Globally unique by code | ATC, AEC, ASC, TSC |
| Instrument | Globally unique (Product+Event+Outcome) | `atc-mls-atl-clt-2026-03-22-draw` |

**Key Rule:** Events belong to exactly one Series. Products are independent and can be applied across any Series. A single event supports multiple products simultaneously.

---

## 2. Product Types (Trading Templates)

### AEC — Athletic Event Contract (Moneyline / Binary)
- Single binary outcome: "Will X win?"
- Instrument ID: `{product}-{event}` (no strike suffix)
- Example: `aec-nfl-ne-den-2026-01-25` → "Will New England win?"

### ATC — Athletic Tie Contract (3-Way Outcome)
- Win/Draw/Lose for sports with draws possible
- Instrument ID: `{product}-{event}-{outcome}` where outcome = `draw`, team abbreviation, or `atc`
- Examples:
  - `atc-mls-atl-clt-2026-03-22-draw` → Draw
  - `atc-mls-atl-clt-2026-03-22-atl` → Atlanta wins

### ASC — Athletic Spread Contract (Point Spreads)
- Directional spread betting
- Instrument ID: `{product}-{event}-pos-{points}` or `neg-{points}`
- Examples:
  - `asc-nfl-hou-mia-2025-12-16-pos-4pt5` → Houston wins by >4.5
  - `asc-nfl-hou-mia-2025-12-16-neg-4pt5` → Houston loses by ≤4.5

### TSC — Total Score Contract (Over/Under)
- Combined score totals
- Instrument ID: `{product}-{event}-{total}` where total = decimal number
- Examples:
  - `tsc-nfl-ne-den-2026-01-25-47-5` → Over 47.5 points
  - `tsc-mls-atl-clt-2026-03-22-2-5` → Over 2.5 goals

### CPC — Crypto Price Contract (Crypto-specific)
- Up/Down, Above/Below, Range, One-Touch markets
- Instrument ID: `{product}-{event}-{strike}` where strike = price level
- Examples:
  - `cpc-btc-updown-15m-2026-09-21-0015z` → Up/Down window
  - `cpc-btc-above-day-2026-09-21-74000` → Above $74,000

---

## 3. Event ID Naming Conventions

| Domain | Format | Example |
|--------|--------|---------|
| Sports (NFL) | `{league}-{home}-{away}-{YYYY-MM-DD}` | `nfl-ne-den-2026-01-25` |
| Sports (MLS) | `{league}-{home}-{away}-{YYYY-MM-DD}` | `mls-atl-clt-2026-03-22` |
| Politics | `{category}-{year}-{MM-DD}` | `uspres-2028-11-05`, `ussen-2026-11-03` |
| Crypto Up/Down | `{asset}-updown-{cadence}-{date}-{HHmmz}` | `btc-updown-15m-2026-09-21-0015z` |
| Crypto Above/Below | `{asset}-above-day-{date}` | `btc-above-day-2026-09-21` |
| Culture (Oscars) | `{event}-{YYYY-MM-DD}` | `oscars-2027-03-28` |

**⚠️ Crypto Warning:** Crypto identifiers are display-only. Always read market type, window, and strike from `assetPriceTerms` metadata — never parse them from the ID string.

---

## 4. Instrument Metadata Fields (from Reference Data API)

### Required Fields
| Field | Type | Description |
|-------|------|-------------|
| `symbol` | string | Globally unique instrument identifier |
| `tickSize` | number | Minimum price increment (usually 0.01) |
| `baseCurrency` | string | Usually "USD" |
| `multiplier` | number | Price multiplier (usually 1; scale = ×100) |
| `minimumTradeQty` | string(decimal) | Smallest valid order quantity in contracts |
| `startDate` | object | Trading start date {year, month, day} |
| `expirationDate` | object | Expiration date {year, month, day} |
| `terminationDate` | object/null | When book is removed from engine |
| `priceLimit.low/high` | string | Absolute price bounds (e.g., "1" to "99") |
| `state` | enum | INSTRUMENT_STATE_OPEN/CLOSED/EXPIRED/TERMINATED/SUSPENDED/HALTED/PREOPEN |

### Metadata Sub-object
| Field | Description |
|-------|-------------|
| `cftc_instrument_id` | CFTC regulatory identifier |
| `long_participant_name` / `short_participant_name` | Team/player names |
| `long_participant_id` / `short_participant_id` | Participant IDs (e.g., "nfl-ne") |
| `instrument_product_series` | Series component (e.g., "mls" from "aec-mls") |
| `event_external_id_sportradar` | Provider ID for sports data |

### Price Scale Rules
- `priceScale: "100"` → prices are in cents ($0.60 = 60)
- `fractionalQtyScale: "0"` → no fractional quantities (integer contracts only)
- `settlementPriceScale: "0"` → settlement at $0 or $1

---

## 5. Market States & Lifecycle

### Instrument Lifecycle
```
PENDING → OPEN → CLOSED → EXPIRED → TERMINATED
         ↑        ↑
      SUSPENDED (cancel allowed, no matching)
      HALTED (no cancel, no matching)
      PREOPEN (enter/modify orders, no matching yet)
      MATCH_AND_CLOSE_AUCTION (matching on state exit)
```

### Market States (from book endpoint)
| State | Meaning |
|-------|---------|
| `MARKET_STATE_OPEN` | Trading active |
| `MARKET_STATE_PREOPEN` | Pre-open phase |
| `MARKET_STATE_SUSPENDED` | Temporarily suspended |
| `MARKET_STATE_HALTED` | Halted (no cancel) |
| `MARKET_STATE_TERMINATED` | Terminated, book removed |

---

## 6. Crypto Price Market Fields (`assetPriceTerms`)

**Only present on crypto markets; null on all others.**

| Field | Type | Description |
|-------|------|-------------|
| `marketType` | enum | UP_DOWN / ABOVE_BELOW / RANGE / ONE_TOUCH / UNSPECIFIED |
| `asset` | object | `{assetClass: "ASSET_CLASS_CRYPTO", symbol: "btc"}` |
| `indexSymbol` | string | Reference index (e.g., "BRTI") |
| `horizon` | string | Cadence: 15m, 1h, hourly, daily, weekly, monthly |
| `windowStart` | timestamp | Measurement window start (UP_DOWN/ONE_TOUCH only) |
| `windowEnd` | timestamp | Settlement instant (use this, NOT endDate) |
| `priceToBeat` | Amount | UP_DOWN reference price (null until stamped ~2s after windowStart) |
| `strike` | Amount | ABOVE_BELOW threshold / ONE_TOUCH target |
| `rangeLower/rangeUpper` | Amount | RANGE bounds (inclusive); open side of tail is null |
| `rangeKind` | enum | INTERIOR / BELOW (bottom tail) / ABOVE (top tail) |
| `direction` | enum | ONE_TOUCH: UP (reaches target from below) / DOWN (dips to it from above) |
| `settlementPrice` | Amount/null | Settled reference price; null on resolved No ONE_TOUCH |

**Filtering:** Use `categories=crypto` parameter when listing markets.

---

## 7. Market Book & BBO Fields

### Full Order Book (`/v1/markets/{slug}/book`)
| Field | Type | Description |
|-------|------|-------------|
| `bids` | array | Buy orders (highest price first) |
| `offers` | array | Sell orders (lowest price first) |
| `state` | string | Current market state |
| `stats` | object | Market statistics |
| `transactTime` | string | Data timestamp |

**Book Entry:** `{px: Amount, qty: string(decimal)}` — qty may contain decimals for partial-contract markets.

### BBO (Lightweight) (`/v1/markets/{slug}/bbo`)
| Field | Type | Description |
|-------|------|-------------|
| `currentPx` | Amount | Current market price |
| `lastTradePx` | Amount | Last trade price |
| `bestBid` / `bestAsk` | Amount | Best bid/ask |
| `bidDepth` / `askDepth` | integer | Number of price levels on each side |
| `sharesTraded` | string | Total shares traded |
| `openInterest` | string | Current open interest |
| `settlementPx` | Amount/null | Settlement price if resolved |

### Market Stats (from book)
| Field | Type | Description |
|-------|------|-------------|
| `openPx` / `closePx` | Amount | Opening/closing prices |
| `highPx` / `lowPx` | Amount | Session high/low |
| `lastTradePx` | Amount | Last trade price |
| `indicativeOpenPx` | Amount | Pre-open indicative price |
| `settlementPx` | Amount | Settlement price |
| `sharesTraded` | string | Total shares traded |
| `notionalTraded` | Amount | Total notional value |
| `lastTradeQty` | string | Last trade quantity |
| `openInterest` | string | Current open interest |
| `currentPx` | Amount | Current market price |

---

## 8. Settlement

- Query: `GET /v1/markets/{slug}/settlement`
- Response: `{slug, settlement: 0.00 or 1.00}`
- For crypto markets with `settlementPrice=null`, use market `status` field instead of waiting on this endpoint.

---

## 9. Gaps Identified (Need More Research)

| Gap | Why It Matters | Related Pass |
|-----|---------------|--------------|
| Participant ID format rules | Needed for bundle arb leg identification | — |
| Sports provider mapping (Sportradar vs SportsDataIO) | Cross-referencing live scores | — |
| Crypto index symbols and their sources | Price-to-beat validation | — |
| Exact tick size per product type | Order submission validation | See Pass 7 (Risk/Constraints) |
| Partial-contract market rules | Quantity alignment for orders | See Pass 3 (Orders API) |

---

## Cross-References

- **Pass 1 (Auth):** Ed25519 signing applies to all instrument/market endpoints
- **Pass 3 (Orders):** `minimumTradeQty` and `orderPriceMinTickSize` from market response must be used before order submission
- **Pass 4 (Portfolio):** Position fields use `*Decimal` versions; settlement maps to `positionResolution` activities
- **Pass 5 (Streaming):** Book updates include `transactTime`; BBO includes `bidDepth`/`askDepth` for liquidity analysis

---

*End of Pass 2. Next: Pass 3 — Order Execution Engine.*
