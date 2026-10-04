# API Routing — Polymarket Exchange Layer Map

> **This is the single authoritative map of every Polymarket API endpoint, its auth layer, rate limits, timeout, retry policy, and which code owns it. No new endpoint is added without updating this file first.**
>
> Last updated: 2026-10-03 → ENDGAME.md §3

## 1. The Four API Layers (from RESEARCH-GUIDE.md §1)

```
┌─────────────────────────────────────────────────────────────────────┐
│  POLYMARKET EXCHANGE (polymarket.us)                               │
├─────────────────────────────────────────────────────────────────────┤
│  L1: Public Gateway   gateway.polymarket.us    Auth: NONE           │
│  L2: Auth API         api.polymarket.us        Auth: Ed25519        │
│  L3: gRPC Streaming   grpc-api.prod.polymarketexchange.com:443      │
│  L4: WebSocket        wss://api.polymarket.us/v1/ws/*               │
└─────────────────────────────────────────────────────────────────────┘
```

**Preprod notes** (from RESEARCH-GUIDE.md §1.1):
- Public Gateway: `gateway.preprod.polymarketexchange.com` → **DNS NOT resolving**
- Auth API: `api.preprod.polymarketexchange.com` → requires JWT Bearer, NOT Ed25519
- Preprod has NOT migrated to Ed25519 auth. Ed25519 keys only work on production.

## 2. Complete Endpoint Map

### L1: Public Gateway (NO AUTH) — owned by `gateway.py`
| Method | Path | Timeout | Rate Limit | Retry | Cached? | Owner |
|--------|------|---------|------------|-------|---------|-------|
| GET | `/v1/markets?limit=200&closed=false` | 10s | 60 req/min | ✅ 3× backoff | ✅ 300s | gateway.py |
| GET | `/v1/markets/{slug}` | 5s | 120 req/min | ✅ 3× | ✅ 300s | gateway.py |
| GET | `/v1/markets/{slug}/book` | 5s | 120 req/min | ✅ 3× | ✅ 60s | gateway.py |
| GET | `/v1/markets/{slug}/bbo` | 5s | 120 req/min | ✅ 3× | ✅ 30s | gateway.py |
| GET | `/v1/events?limit=100` | 10s | 60 req/min | ✅ 3× | ✅ 600s | gateway.py |
| GET | `/v1/series` | 10s | 60 req/min | ✅ 3× | ✅ 600s | gateway.py |
| GET | `/v1/sports` | 10s | 60 req/min | ✅ 3× | ✅ 600s | gateway.py |
| GET | `/v1/search?q=...&limit=50` | 10s | 30 req/min | ✅ 3× | ✅ 300s | gateway.py |
| GET | `/v1/health` | 5s | 1 req/10s | ❌ | ❌ | gateway.py |

**Issues in gateway.py (current code):**
- ❌ No rate limiter implemented (only timeouts). Polymarket returns 429 on excess.
- ❌ No exponential backoff on retry (just "3×" in map — code has no retry loop).
- ❌ No circuit breaker on `requests.get` (fuse_panel exists but isn't wired).
- ❌ No request/response logging for debugging.
- ❌ No connection pooling (new session per call, not per class).
- ❌ `get_markets` returns `[]` on any exception — swallows 403/429/500.

### L2: Authenticated API (Ed25519) — owned by `executor.py`
| Method | Path | Timeout | Rate Limit | Retry | Auth | Owner |
|--------|------|---------|------------|-------|------|-------|
| POST | `/v1/orders` | 10s | 30 req/min | ✅ 3× | JWT (RSA/RS256) | executor.py |
| GET | `/v1/markets/{slug}` | 5s | 120 req/min | ✅ 3× | JWT | executor.py |
| GET | `/v1/orders/open` | 5s | 30 req/min | ✅ 3× | JWT | executor.py |
| POST | `/v1/order/{id}/cancel` | 5s | 30 req/min | ✅ 3× | JWT | executor.py |
| POST | `/v1/orders/open/cancel` | 5s | 30 req/min | ✅ 3× | JWT | executor.py |
| GET | `/v1/portfolio/positions` | 5s | 30 req/min | ✅ 3× | JWT | executor.py |
| GET | `/v1/account/balances` | 5s | 30 req/min | ✅ 3× | JWT | executor.py |
| GET | `/v1/portfolio/activities?limit=50` | 5s | 30 req/min | ✅ 3× | JWT | executor.py |

**Issues in executor.py (current code):**
- ❌ Uses RSA/RS256 JWT (Auth0 client_credentials flow), NOT Ed25519.
- ❌ Token refresh logic: `get_token()` only refreshes if `time < expires_at - 30`. If `expires_at` is wrong, it re-auths every call.
- ❌ No Ed25519 signing at all (SDK v2.1.0 uses `X-PM-Access-Key`, `X-PM-Timestamp`, `X-PM-Signature` headers).
- ❌ Token is instance-scoped (recreated per `PolymarketExecutor` call — no sharing).
- ❌ `_place_order` converts USDC→quantity via `size_usdc / price` but doesn't validate the result against Polymarket's min order size.
- ❌ No idempotency key on POST `/v1/orders`.
- ❌ No partial-fill handling.
- ❌ No WebSocket auth (placeholder only: `"X-PM-Signature": "would be computed here"`).

### L3: gRPC Streaming — NOT IMPLEMENTED
| Method | Path | Auth | Status |
|--------|------|------|--------|
| Subscribe | `grpc-api.prod.polymarketexchange.com:443` | JWT Bearer (M2M OAuth) | ❌ Not coded |
| Unsubscribe | same | JWT Bearer | ❌ |
| Stream markets | same | JWT Bearer | ❌ |
| Stream orders/positions | same | JWT Bearer | ❌ |

### L4: WebSocket — partial implementation (`executor.py` WebSocketClient)
| Subscription | URL | Auth | Status |
|-------------|-----|------|--------|
| Markets (order book) | `wss://api.polymarket.us/v1/ws/markets` | JWT Bearer | ⚠️ Skeleton only |
| Private (orders/positions) | `wss://api.polymarket.us/v1/ws/private` | JWT Bearer | ⚠️ Skeleton only |

**Issues in WebSocketClient:**
- ❌ `_get_auth_headers` is a stub — signature computation is commented out.
- ❌ No reconnection logic, no ping/pong health check, no message queue.
- ❌ No `websockets` import in `requirements.txt` (it's in `executor.py` as `import websockets`).
- ❌ Subscription type 1/3/4 are magic numbers, no constants.

### L5: Polymarket Cache (JSON TTL) — owned by `polymarket_cache.py`
| Key Pattern | TTL | Stored in |
|-------------|-----|-----------|
| `market:{slug}` | 300s | `cache/polymarket_cache.json` |
| `orderbook:{slug}` | 60s | same |
| `price:{slug}` | 30s | same |
| `positions` | 120s | same |
| `portfolio` | 60s | same |
| `activities` | 300s | same |
| `events` | 600s | same |

**Issues:**
- ❌ TTLs are hardcoded, not configurable per-endpoint.
- ❌ No TTL override from the routing layer (gateway knows its own limits).
- ❌ Cache file is NOT transactional (write → crash → corrupt JSON).

## 3. Agent/Renderer Layer (Electron app) — owned by `agent/main.py`
This is a **duplicate auth layer**. `agent/main.py` has its own `PolymarketClient` class with its own RSA JWT auth, separate from `executor.py`. It also has its own `requests.Session`.

| Method | Path | Auth | Status |
|--------|------|------|--------|
| POST | `/oauth/token` (Auth0) | RSA JWT | ✅ |
| GET/POST | `/v1/*` (API) | Bearer JWT | ✅ |
| WS | `wss://api...*` | JWT | ✅ |

**Problem**: There are now 3 auth layers (gateway.py, executor.py, agent/main.py). They are NOT synchronized. If one layer's token expires, the others don't know.

## 4. Routing Rules (Non-Negotiable)

1. **One gateway per layer**: L1 → `gateway.py`, L2/L3/L4 → `executor.py`. No new `requests.get()` calls anywhere outside these two modules.
2. **One auth manager per layer**: L1 has no auth. L2/L3/L4 share ONE `TokenManager` (singleton). `agent/main.py` must NOT have its own JWT logic — it must call `executor.TokenManager.get_token()`.
3. **All cache TTLs flow through the routing layer**: `gateway.py` sets TTLs per endpoint. `polymarket_cache.py` just stores whatever TTL it's given. No hardcoded TTLs in the cache module.
4. **All rate limits are enforced at the routing layer**: `gateway.py` has a token bucket per endpoint. `executor.py` has a separate bucket for authenticated endpoints (tighter: 30/min vs 120/min).
5. **No endpoint is added without a row in this table** (Section 2). If you add a new endpoint, you update this table AND add a test.

## 5. Auth Flow (Production)

```
1. Agent loads `agent/config.yaml` → reads `client_id`, `audience`, `rsa_key_path`
2. On first API call: TokenManager loads RSA key from disk → signs RS256 JWT → POSTs to Auth0 `oauth/token` → gets access_token
3. access_token is cached (expires_at - 30s buffer) → attached as `Authorization: Bearer <token>`
4. On 401: refresh token, retry once. If still 401 → FAIL (key is wrong / revoked)
5. ⚠️ Ed25519 path (SDK v2.1.0): `from polymarket_us import PolymarketUS` → `X-PM-*` headers. NOT yet implemented. This is a gap.

⚠️ Preprod: JWT Bearer only (no Ed25519 support). Requires Auth0 client credentials on `pmx-preprod.us.auth0.com`.
```

## 6. Missing (Must Be Built Before Real Trading)

| # | Missing | Why It Matters |
|---|---------|---------------|
| 1 | Ed25519 signing (SDK v2.1.0 path) | RSA JWT works but Ed25519 is the official SDK. If RSA path is deprecated, everything breaks. |
| 2 | TokenManager singleton across all modules | Right now gateway.py, executor.py, and agent/main.py each have their own token. If one expires, others keep using stale tokens → 401 storms. |
| 3 | Rate limiter (token bucket) in gateway.py | Polymarket returns 429. Current code just sleeps 10s and retries 3×. With 200 markets, that's 600 reqs — a DoS to their API. |
| 4 | Circuit breaker on gateway.py | fuse_panel exists but isn't wired. If gateway.py goes down, the engine keeps hammering it → wasted CPU + rate limit. |
| 5 | Idempotency on POST `/v1/orders` | No `idempotency_key` header. Network timeout → retry → double order. |
| 6 | Partial-fill handling | Polymarket fills partially. Current `executor.py` assumes full fill or failure. |
| 7 | gRPC streaming client | WebSocket is skeleton-only. gRPC is the production streaming layer. |
| 8 | Unified auth abstraction | 3 auth layers (gateway, executor, agent) must merge into ONE. |

## 7. Verification

Before merging any code that touches API routing:
- `grep -rn "requests\." F:/PolyMarket/poly-agent/` → must be ONLY in `gateway.py` and `executor.py`
- `grep -rn "import jwt\|import rsa\|RSA" F:/PolyMarket/poly-agent/` → must be ONLY in `executor.py`
- `grep -rn "requests.Session()" F:/PolyMarket/poly-agent-app/agent/main.py` → must be removed or redirected to executor.TokenManager
- `python -c "from mcp_server.persistence.polymarket_cache import PolymarketCache"` → must import (no non-ASCII filename bug)
