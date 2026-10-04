# Polymarket US Developer Reference Index
> Custom build context target for production LLM code generation and RAG pipelines.

## Section: Getting Started
---

### Introduction
**Source Routing Target:** https://docs.polymarket.us/api-reference/introduction

```text
The Polymarket US API is split into two parts: an authenticated API for trading and a public API for reading market data. For support, contact
support@polymarket.us
.
​
Authenticated API
https://api.polymarket.us
Use the authenticated API to trade. This is where you place orders, check your positions, and manage your account. Every request requires an API key - see
Authentication
to get set up.
Group
What you get
Orders
Place, modify, cancel, and query orders
Portfolio
View positions and trading activity
Account
Check balances and buying power
The authenticated API also provides two WebSocket endpoints for real-time streaming:
Endpoint
Purpose
wss://api.polymarket.us/v1/ws/private
Real-time order, position, and balance updates
wss://api.polymarket.us/v1/ws/markets
Real-time order book and trade streaming
​
Public API
https://gateway.polymarket.us
Use the public API to browse what’s available on Polymarket US. No API key needed. This is where you fetch markets, events, series, sports data, and search results. If you’re building something that displays market information - prices, odds, order books - this is all you need.
Group
What you get
Markets
List markets, get order books, BBO, settlement prices, and price history
Events
List events, get event details
Series
List series (e.g., NFL 2025-26 Season)
Sports
Leagues, teams, game schedules
Search
Full-text search across events and markets
```

### Rate Limits
**Source Routing Target:** https://docs.polymarket.us/getting-started/rate-limits

```text
ERROR: Status code 404
```

### Authentication
**Source Routing Target:** https://docs.polymarket.us/getting-started/authentication

```text
ERROR: Status code 404
```

## Section: Orders
---

### Orders API Overview
**Source Routing Target:** https://docs.polymarket.us/api-reference/orders/overview

```text
​
Orders API
The Orders API provides order entry and management capabilities for trading on markets.
Authentication Required
All Orders API endpoints require API key authentication. See the
Authentication guide
for details on signing requests.
​
Base URL
https://api.polymarket.us
​
Endpoints
​
Order Entry
Method
Endpoint
Description
POST
/v1/orders
Create a new order
POST
/v1/order/preview
Preview order before submission
POST
/v1/order/close-position
Close an existing position
​
Order Query
Method
Endpoint
Description
GET
/v1/orders/open
Get all open orders
GET
/v1/order/{orderId}
Get a specific order by ID
​
Order Management
Method
Endpoint
Description
POST
/v1/order/{orderId}/modify
Modify an existing order
POST
/v1/order/{orderId}/cancel
Cancel a specific order
POST
/v1/orders/open/cancel
Cancel all open orders
​
Batched Operations
Up to 20 orders per call.
Method
Endpoint
Description
POST
/v1/orders/batched
Create up to 20 orders in a single request
POST
/v1/orders/batched/cancel
Cancel up to 20 specific orders by ID
POST
/v1/orders/batched/modify
Modify up to 20 existing orders (each forwarded to the exchange as a cancel-replace)
Note:
/v1/orders/open/cancel
cancels
all
of your open orders (optionally filtered by market). Use
/v1/orders/batched/cancel
when you want to cancel a specific list of order IDs.
Batched responses do not confirm per-entry success.
Gateway validation is atomic: if any entry fails request-shape checks (missing
orderId
, batch > 20, etc.), the whole batch is rejected with
400
.
The exchange processes entries independently. An unknown
orderId
in a batched cancel or modify is silently ignored.
canceledOrderIds
and
modifiedOrderIds
echo the request; they do not certify that each ID was acted on. For real outcomes, subscribe to the
Private WebSocket order stream
and watch for
EXECUTION_TYPE_REPLACE
,
EXECUTION_TYPE_CANCELED
, and
EXECUTION_TYPE_REJECTED
.
createdOrderIds
from
/v1/orders/batched
are real exchange-assigned IDs, but per-order accept/fill/reject events still come via the order stream.
​
Order Types
All enum values are passed as
strings
in the request body:
Value
Description
ORDER_TYPE_LIMIT
Limit order at specified price
ORDER_TYPE_MARKET
Market order executed at best available price
Example:
{
"type"
:
"ORDER_TYPE_LIMIT"
}
​
Order Intent
Orders require an intent indicating position direction. Pass these as
string
values:
Value
Description
ORDER_INTENT_BUY_LONG
Buy YES contracts (go long on Yes outcome)
ORDER_INTENT_SELL_LONG
Sell YES contracts (close long Yes position)
ORDER_INTENT_BUY_SHORT
Buy NO contracts (go long on No outcome)
ORDER_INTENT_SELL_SHORT
Sell NO contracts (close long No position)
Example - Buy NO contracts:
{
"marketSlug"
:
"your-market-slug"
,
"type"
:
"ORDER_TYPE_LIMIT"
,
"price"
: {
"value"
:
"0.45"
,
"currency"
:
"USD"
},
"quantity"
:
10
,
"tif"
:
"TIME_IN_FORCE_GOOD_TILL_CANCEL"
,
"intent"
:
"ORDER_INTENT_BUY_SHORT"
}
​
Alternative: Outcome Side + Action
Instead of
intent
, you can specify the equivalent
outcomeSide
+
action
pair. Both forms are accepted on
CreateOrder
and the batched variants. If both are sent,
outcomeSide
+
action
wins.
outcomeSide
action
Equivalent
intent
OUTCOME_SIDE_YES
ORDER_ACTION_BUY
ORDER_INTENT_BUY_LONG
OUTCOME_SIDE_YES
ORDER_ACTION_SELL
ORDER_INTENT_SELL_LONG
OUTCOME_SIDE_NO
ORDER_ACTION_BUY
ORDER_INTENT_BUY_SHORT
OUTCOME_SIDE_NO
ORDER_ACTION_SELL
ORDER_INTENT_SELL_SHORT
Example: same “buy NO contracts” order, expressed with outcomeSide + action:
{
"marketSlug"
:
"your-market-slug"
,
"type"
:
"ORDER_TYPE_LIMIT"
,
"price"
: {
"value"
:
"0.45"
,
"currency"
:
"USD"
},
"quantity"
:
10
,
"tif"
:
"TIME_IN_FORCE_GOOD_TILL_CANCEL"
,
"outcomeSide"
:
"OUTCOME_SIDE_NO"
,
"action"
:
"ORDER_ACTION_BUY"
}
The
Order
returned by
GET /v1/order/{orderId}
and
GET /v1/orders/open
includes both
intent
and
outcomeSide
+
action
, so you can read whichever you prefer. The price-vs-side rules below apply to both forms.
​
Understanding Price with Order Intent
Only the long side (YES) is directly tradable. The short side (NO) is synthetic exposure created through positions in the long side. The
price.value
field always represents the long side’s price, regardless of which order intent you use. In the market slug, the first team is always the long/YES side and the second team is the short/NO side. A common mistake is attempting to buy both YES at 0.60 and NO at 0.40, which causes a self-match error. Since YES and NO prices must sum to $1.00, buying NO at 0.40 is equivalent to buying YES at 0.60 - you’re placing two buy orders at the same price level on the same instrument. If you want exposure to both sides, use different price levels (e.g., buy YES at 0.55 and buy NO at 0.50).
Example:
For market
aec-cbb-usc-iowa-2026-01-28
:
YES (long side) = USC
NO (short side) = Iowa
price.value
always refers to USC’s price
How This Affects Your Orders:
You Want To
Order Intent
price.value
Buy USC at 0.83
ORDER_INTENT_BUY_LONG
0.83
Sell USC at 0.83
ORDER_INTENT_SELL_LONG
0.83
Buy Iowa at 0.83
ORDER_INTENT_BUY_SHORT
0.17
Sell Iowa at 0.83
ORDER_INTENT_SELL_SHORT
0.17
In binary markets, YES and NO are inverses: buying NO at 0.83 is equivalent to buying YES at 0.17 (1.00 - 0.83). Since
price.value
always represents the YES side, you must set it to 0.17 when trading Iowa (NO) at 0.83. To trade the NO side at any price X, set
price.value = 1.00 - X
.
​
Price Validation
Orders must have
price.value
between 0.01 and 0.99 (the exchange’s absolute price limits).
Invalid prices (below 0.01 or above 0.99) are restricted at the exchange level.
Since the order is sent to the exchange, you will still receive an orderID, but the order will never fill because it gets rejected during validation.
Example:
{
"price"
: {
"value"
:
"45"
,
"currency"
:
"USD"
}
// Invalid - will receive orderID but order rejected
}
Always validate price bounds client-side before submission to avoid unnecessary orderIDs for rejected orders.
​
Quantity and Tick Size by Market
Markets can differ in both minimum order quantity and minimum price increment. Read these fields from the market response before submitting or modifying an order:
Market field
Use
minimumTradeQty
Smallest valid
quantity
, expressed in contracts. A value of
0.01
means 1% of a contract.
orderPriceMinTickSize
Smallest valid
price.value
increment. A value of
0.005
means half-cent ticks.
The
quantity
field on order requests and order responses is a number and can contain decimals for partial-contract markets. Submit
quantity
and
price.value
already aligned to the market’s
minimumTradeQty
and
orderPriceMinTickSize
. Extra precision is not part of the public contract and can be normalized to the market precision; for example, on a market with
minimumTradeQty: 0.01
and
orderPriceMinTickSize: 0.01
,
quantity: 0.015
can be accepted and returned as
0.01
, and
price.value: "0.515"
can be returned as
"0.51"
.
​
Order Side
The order side indicates buy or sell direction:
Value
Description
ORDER_SIDE_BUY
Buy order
ORDER_SIDE_SELL
Sell order
​
Order States
Orders progress through these states:
PENDING_NEW → PARTIALLY_FILLED → FILLED
↓
CANCELED / REJECTED / EXPIRED
State
Value
Description
ORDER_STATE_PENDING_NEW
7
Order received, not yet processed by matching engine
ORDER_STATE_NEW
0
Order accepted by matching engine and resting on the book
ORDER_STATE_PENDING_REPLACE
8
Modify request received, not yet processed
ORDER_STATE_PENDING_CANCEL
9
Cancel request received, not yet processed
ORDER_STATE_PENDING_RISK
10
Order pending risk approval
ORDER_STATE_PARTIALLY_FILLED
1
Order partially executed
ORDER_STATE_FILLED
2
Order fully executed
ORDER_STATE_CANCELED
3
Order canceled
ORDER_STATE_REPLACED
4
Order replaced via modify (cancel-replace)
ORDER_STATE_REJECTED
5
Order rejected by exchange
ORDER_STATE_EXPIRED
6
Order expired (GTD orders)
​
Time in Force
Value
Description
TIME_IN_FORCE_DAY
DAY - Expires at the end of the trading day
TIME_IN_FORCE_GOOD_TILL_CANCEL
GTC - Remains active until filled or canceled
TIME_IN_FORCE_GOOD_TILL_DATE
GTD - Expires at specified
goodTillTime
TIME_IN_FORCE_IMMEDIATE_OR_CANCEL
IOC - Fills immediately available quantity, cancels rest
TIME_IN_FORCE_FILL_OR_KILL
FOK - Must fill entirely or cancel completely
DAY orders do not automatically cancel at 5pm during trade day rolls.
The Exchange team is working on improving the DAY order types performance. While the Exchange makes improvement, DAY orders will not automatically cancel at 5pm during trade day rolls. Please use GTD orders with the desired timestamp. GTD orders will remain functional with the good-til-time specified.
​
Manual Order Indicator
Required to indicate whether the order is placed by a human or automated system:
Value
Description
MANUAL_ORDER_INDICATOR_MANUAL
Order placed manually by a user
MANUAL_ORDER_INDICATOR_AUTOMATIC
Order placed by an automated trading system
​
Execution Types
Execution events returned in synchronous order responses:
Value
Description
EXECUTION_TYPE_NEW
Order accepted (new working order confirmation)
EXECUTION_TYPE_PARTIAL_FILL
Order partially filled
EXECUTION_TYPE_FILL
Order fully filled
EXECUTION_TYPE_CANCELED
Order canceled
EXECUTION_TYPE_REPLACE
Order replaced/modified
EXECUTION_TYPE_REJECTED
Order rejected
EXECUTION_TYPE_EXPIRED
Order expired
EXECUTION_TYPE_DONE_FOR_DAY
Order done for the trading day
​
Order Reject Reasons
If an order is rejected, the reason will be one of:
Value
Description
ORD_REJECT_REASON_EXCHANGE_OPTION
Generic exchange-defined reason (used when no more specific code applies)
ORD_REJECT_REASON_UNKNOWN_MARKET
Unknown or invalid market
ORD_REJECT_REASON_EXCHANGE_CLOSED
Exchange/market is closed
ORD_REJECT_REASON_INCORRECT_QUANTITY
Invalid quantity
ORD_REJECT_REASON_INVALID_PRICE_INCREMENT
Price not on valid increment
ORD_REJECT_REASON_INCORRECT_ORDER_TYPE
Invalid order type for market
ORD_REJECT_REASON_PRICE_OUT_OF_BOUNDS
Price outside valid range
ORD_REJECT_REASON_NO_LIQUIDITY
No liquidity for market order
​
Slippage Tolerance
For market orders or close position orders, you can specify slippage tolerance:
{
"slippageTolerance"
: {
"currentPrice"
: {
"value"
:
"0.50"
,
"currency"
:
"USD"
},
"ticks"
:
5
}
}
Field
Type
Description
currentPrice
Amount
Reference price for slippage calculation
bips
integer
Slippage tolerance in basis points (1 bip = 0.01%)
ticks
integer
Slippage tolerance in price ticks (takes priority over bips)
​
Default Values
slippageTolerance
is optional and defaults to:
Market orders
: Unlimited (no slippage protection by default)
Limit orders
: Not applicable (price is fixed)
Slippage tolerance defines the maximum price movement you’ll accept. For example, if you submit a market order to buy at current price 0.50 with
ticks: 5
, the order will reject if the best ask moves above 0.55 before execution.
Real-Time Order Updates
After submitting orders via REST, use the
WebSocket Private Stream
to receive real-time updates on order status, fills, and cancellations.
​
Complete Create Order Example
{
"marketSlug"
:
"your-market-slug"
,
"type"
:
"ORDER_TYPE_LIMIT"
,
"price"
: {
"value"
:
"0.555"
,
"currency"
:
"USD"
},
"quantity"
:
0.5
,
"tif"
:
"TIME_IN_FORCE_GOOD_TILL_CANCEL"
,
"intent"
:
"ORDER_INTENT_BUY_LONG"
,
"manualOrderIndicator"
:
"MANUAL_ORDER_INDICATOR_MANUAL"
,
"participateDontInitiate"
:
false
}
​
Rate Limits
The API enforces a global rate limit of
20 requests per second
per API key across all endpoints.
Rate Limit Exceeded
When rate limits are exceeded, the API returns HTTP status
429 Too Many Requests
.
Notes:
Rate limits are enforced at the edge (Cloudflare) before requests reach the API
Limits are applied per API key
Implement exponential backoff and request throttling in your application
​
Best Practices
Use string enum values
- All enums are passed as strings (e.g.,
"ORDER_TYPE_LIMIT"
, not
1
)
Use WebSocket for updates
- Subscribe to order updates instead of polling
Preview before submit
- Use the preview endpoint for order validation
Handle rejects
- Implement proper error handling for rejected orders
Use asynchronous execution for limit orders
- For market-making and resting limit orders, avoid
synchronousExecution: true
as it waits up to 10 seconds for final order state. Instead, submit orders asynchronously (the default) and poll with
GET /v1/order/{orderId}
to check status (~100ms). Only use
synchronousExecution: true
for immediately-fillable orders where you need to wait for fill confirmation.
Specify manual order indicator
- Required for regulatory compliance
Respect rate limits
- Implement request throttling to stay within rate limits and avoid 429 errors
```

### Get Order (GET)
**Source Routing Target:** https://docs.polymarket.us/api-reference/orders/get-order

```text
Get Order
cURL
curl --request GET \
--url https://api.polymarket.us/v1/order/{orderId} \
--header 'X-PM-Access-Key: <api-key>' \
--header 'X-PM-Signature: <api-key>' \
--header 'X-PM-Timestamp: <api-key>'
import requests
url = "https://api.polymarket.us/v1/order/{orderId}"
headers = {
"X-PM-Access-Key": "<api-key>",
"X-PM-Timestamp": "<api-key>",
"X-PM-Signature": "<api-key>"
}
response = requests.get(url, headers=headers)
print(response.text)
const options = {
method: 'GET',
headers: {
'X-PM-Access-Key': '<api-key>',
'X-PM-Timestamp': '<api-key>',
'X-PM-Signature': '<api-key>'
}
};
fetch('https://api.polymarket.us/v1/order/{orderId}', options)
.then(res => res.json())
.then(res => console.log(res))
.catch(err => console.error(err));
<?php
$curl = curl_init();
curl_setopt_array($curl, [
CURLOPT_URL => "https://api.polymarket.us/v1/order/{orderId}",
CURLOPT_RETURNTRANSFER => true,
CURLOPT_ENCODING => "",
CURLOPT_MAXREDIRS => 10,
CURLOPT_TIMEOUT => 30,
CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
CURLOPT_CUSTOMREQUEST => "GET",
CURLOPT_HTTPHEADER => [
"X-PM-Access-Key: <api-key>",
"X-PM-Signature: <api-key>",
"X-PM-Timestamp: <api-key>"
],
]);
$response = curl_exec($curl);
$err = curl_error($curl);
curl_close($curl);
if ($err) {
echo "cURL Error #:" . $err;
} else {
echo $response;
}
package main
import (
"fmt"
"net/http"
"io"
)
func main() {
url := "https://api.polymarket.us/v1/order/{orderId}"
req, _ := http.NewRequest("GET", url, nil)
req.Header.Add("X-PM-Access-Key", "<api-key>")
req.Header.Add("X-PM-Timestamp", "<api-key>")
req.Header.Add("X-PM-Signature", "<api-key>")
res, _ := http.DefaultClient.Do(req)
defer res.Body.Close()
body, _ := io.ReadAll(res.Body)
fmt.Println(string(body))
}
HttpResponse<String> response = Unirest.get("https://api.polymarket.us/v1/order/{orderId}")
.header("X-PM-Access-Key", "<api-key>")
.header("X-PM-Timestamp", "<api-key>")
.header("X-PM-Signature", "<api-key>")
.asString();
require 'uri'
require 'net/http'
url = URI("https://api.polymarket.us/v1/order/{orderId}")
http = Net::HTTP.new(url.host, url.port)
http.use_ssl = true
request = Net::HTTP::Get.new(url)
request["X-PM-Access-Key"] = '<api-key>'
request["X-PM-Timestamp"] = '<api-key>'
request["X-PM-Signature"] = '<api-key>'
response = http.request(request)
puts response.read_body
200
{
"order": {
"id": "<string>",
"marketSlug": "<string>",
"side": "ORDER_SIDE_BUY",
"type": "ORDER_TYPE_LIMIT",
"price": {
"value": "0.55",
"currency": "USD"
},
"quantity": 123,
"cumQuantity": 123,
"leavesQuantity": 123,
"tif": "TIME_IN_FORCE_DAY",
"goodTillTime": "2023-11-07T05:31:56Z",
"intent": "ORDER_INTENT_BUY_LONG",
"marketMetadata": {
"slug": "<string>",
"icon": "<string>",
"title": "<string>",
"outcome": "<string>",
"eventSlug": "<string>",
"teamId": 123,
"team": {
"id": 123,
"name": "<string>",
"abbreviation": "<string>",
"league": "<string>",
"record": "<string>",
"logo": "<string>",
"alias": "<string>",
"safeName": "<string>",
"homeIcon": "<string>",
"awayIcon": "<string>",
"colorPrimary": "<string>",
"ordering": "<string>",
"ranking": "<string>",
"conference": "<string>"
}
},
"state": "ORDER_STATE_NEW",
"commissionNotionalTotalCollected": {
"value": "0.55",
"currency": "USD"
},
"commissionsBasisPoints": "<string>",
"makerCommissionsBasisPoints": "<string>",
"avgPx": {
"value": "0.55",
"currency": "USD"
},
"cashOrderQty": {
"value": "0.55",
"currency": "USD"
},
"insertTime": "2023-11-07T05:31:56Z",
"createTime": "2023-11-07T05:31:56Z",
"outcomeSide": "OUTCOME_SIDE_YES",
"action": "ORDER_ACTION_BUY"
}
}
GET
/
v1
/
order
/
{orderId}
Try it
Get Order
cURL
curl --request GET \
--url https://api.polymarket.us/v1/order/{orderId} \
--header 'X-PM-Access-Key: <api-key>' \
--header 'X-PM-Signature: <api-key>' \
--header 'X-PM-Timestamp: <api-key>'
import requests
url = "https://api.polymarket.us/v1/order/{orderId}"
headers = {
"X-PM-Access-Key": "<api-key>",
"X-PM-Timestamp": "<api-key>",
"X-PM-Signature": "<api-key>"
}
response = requests.get(url, headers=headers)
print(response.text)
const options = {
method: 'GET',
headers: {
'X-PM-Access-Key': '<api-key>',
'X-PM-Timestamp': '<api-key>',
'X-PM-Signature': '<api-key>'
}
};
fetch('https://api.polymarket.us/v1/order/{orderId}', options)
.then(res => res.json())
.then(res => console.log(res))
.catch(err => console.error(err));
<?php
$curl = curl_init();
curl_setopt_array($curl, [
CURLOPT_URL => "https://api.polymarket.us/v1/order/{orderId}",
CURLOPT_RETURNTRANSFER => true,
CURLOPT_ENCODING => "",
CURLOPT_MAXREDIRS => 10,
CURLOPT_TIMEOUT => 30,
CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
CURLOPT_CUSTOMREQUEST => "GET",
CURLOPT_HTTPHEADER => [
"X-PM-Access-Key: <api-key>",
"X-PM-Signature: <api-key>",
"X-PM-Timestamp: <api-key>"
],
]);
$response = curl_exec($curl);
$err = curl_error($curl);
curl_close($curl);
if ($err) {
echo "cURL Error #:" . $err;
} else {
echo $response;
}
package main
import (
"fmt"
"net/http"
"io"
)
func main() {
url := "https://api.polymarket.us/v1/order/{orderId}"
req, _ := http.NewRequest("GET", url, nil)
req.Header.Add("X-PM-Access-Key", "<api-key>")
req.Header.Add("X-PM-Timestamp", "<api-key>")
req.Header.Add("X-PM-Signature", "<api-key>")
res, _ := http.DefaultClient.Do(req)
defer res.Body.Close()
body, _ := io.ReadAll(res.Body)
fmt.Println(string(body))
}
HttpResponse<String> response = Unirest.get("https://api.polymarket.us/v1/order/{orderId}")
.header("X-PM-Access-Key", "<api-key>")
.header("X-PM-Timestamp", "<api-key>")
.header("X-PM-Signature", "<api-key>")
.asString();
require 'uri'
require 'net/http'
url = URI("https://api.polymarket.us/v1/order/{orderId}")
http = Net::HTTP.new(url.host, url.port)
http.use_ssl = true
request = Net::HTTP::Get.new(url)
request["X-PM-Access-Key"] = '<api-key>'
request["X-PM-Timestamp"] = '<api-key>'
request["X-PM-Signature"] = '<api-key>'
response = http.request(request)
puts response.read_body
200
{
"order": {
"id": "<string>",
"marketSlug": "<string>",
"side": "ORDER_SIDE_BUY",
"type": "ORDER_TYPE_LIMIT",
"price": {
"value": "0.55",
"currency": "USD"
},
"quantity": 123,
"cumQuantity": 123,
"leavesQuantity": 123,
"tif": "TIME_IN_FORCE_DAY",
"goodTillTime": "2023-11-07T05:31:56Z",
"intent": "ORDER_INTENT_BUY_LONG",
"marketMetadata": {
"slug": "<string>",
"icon": "<string>",
"title": "<string>",
"outcome": "<string>",
"eventSlug": "<string>",
"teamId": 123,
"team": {
"id": 123,
"name": "<string>",
"abbreviation": "<string>",
"league": "<string>",
"record": "<string>",
"logo": "<string>",
"alias": "<string>",
"safeName": "<string>",
"homeIcon": "<string>",
"awayIcon": "<string>",
"colorPrimary": "<string>",
"ordering": "<string>",
"ranking": "<string>",
"conference": "<string>"
}
},
"state": "ORDER_STATE_NEW",
"commissionNotionalTotalCollected": {
"value": "0.55",
"currency": "USD"
},
"commissionsBasisPoints": "<string>",
"makerCommissionsBasisPoints": "<string>",
"avgPx": {
"value": "0.55",
"currency": "USD"
},
"cashOrderQty": {
"value": "0.55",
"currency": "USD"
},
"insertTime": "2023-11-07T05:31:56Z",
"createTime": "2023-11-07T05:31:56Z",
"outcomeSide": "OUTCOME_SIDE_YES",
"action": "ORDER_ACTION_BUY"
}
}
Authorizations
​
X-PM-Access-Key
string
header
required
Your API key ID (UUID). Generate at
polymarket.us/developer
.
​
X-PM-Timestamp
string
header
required
Unix timestamp in milliseconds. Must be within 30 seconds of server time.
​
X-PM-Signature
string
header
required
Base64-encoded Ed25519 signature of
timestamp + method + path
. See
Authentication
for details.
Path Parameters
​
orderId
string
required
Exchange-assigned Order ID to retrieve
Response
200
application/json
Order retrieved successfully
Response containing order details
​
order
object
The requested order
Show
child attributes
```

### Get Open Orders (GET)
**Source Routing Target:** https://docs.polymarket.us/api-reference/orders/get-open-orders

```text
Get Open Orders
cURL
curl
--request
GET
\
--url
https://api.polymarket.us/v1/orders/open
\
--header
'X-PM-Access-Key: <api-key>'
\
--header
'X-PM-Signature: <api-key>'
\
--header
'X-PM-Timestamp: <api-key>'
import requests
url = "https://api.polymarket.us/v1/orders/open"
headers = {
"X-PM-Access-Key": "<api-key>",
"X-PM-Timestamp": "<api-key>",
"X-PM-Signature": "<api-key>"
}
response = requests.get(url, headers=headers)
print(response.text)
const options = {
method: 'GET',
headers: {
'X-PM-Access-Key': '<api-key>',
'X-PM-Timestamp': '<api-key>',
'X-PM-Signature': '<api-key>'
}
};
fetch('https://api.polymarket.us/v1/orders/open', options)
.then(res => res.json())
.then(res => console.log(res))
.catch(err => console.error(err));
<?php
$curl = curl_init();
curl_setopt_array($curl, [
CURLOPT_URL => "https://api.polymarket.us/v1/orders/open",
CURLOPT_RETURNTRANSFER => true,
CURLOPT_ENCODING => "",
CURLOPT_MAXREDIRS => 10,
CURLOPT_TIMEOUT => 30,
CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
CURLOPT_CUSTOMREQUEST => "GET",
CURLOPT_HTTPHEADER => [
"X-PM-Access-Key: <api-key>",
"X-PM-Signature: <api-key>",
"X-PM-Timestamp: <api-key>"
],
]);
$response = curl_exec($curl);
$err = curl_error($curl);
curl_close($curl);
if ($err) {
echo "cURL Error #:" . $err;
} else {
echo $response;
}
package main
import (
"fmt"
"net/http"
"io"
)
func main() {
url := "https://api.polymarket.us/v1/orders/open"
req, _ := http.NewRequest("GET", url, nil)
req.Header.Add("X-PM-Access-Key", "<api-key>")
req.Header.Add("X-PM-Timestamp", "<api-key>")
req.Header.Add("X-PM-Signature", "<api-key>")
res, _ := http.DefaultClient.Do(req)
defer res.Body.Close()
body, _ := io.ReadAll(res.Body)
fmt.Println(string(body))
}
HttpResponse<String> response = Unirest.get("https://api.polymarket.us/v1/orders/open")
.header("X-PM-Access-Key", "<api-key>")
.header("X-PM-Timestamp", "<api-key>")
.header("X-PM-Signature", "<api-key>")
.asString();
require 'uri'
require 'net/http'
url = URI("https://api.polymarket.us/v1/orders/open")
http = Net::HTTP.new(url.host, url.port)
http.use_ssl = true
request = Net::HTTP::Get.new(url)
request["X-PM-Access-Key"] = '<api-key>'
request["X-PM-Timestamp"] = '<api-key>'
request["X-PM-Signature"] = '<api-key>'
response = http.request(request)
puts response.read_body
200
{
"orders"
: [
{
"id"
:
"<string>"
,
"marketSlug"
:
"<string>"
,
"side"
:
"ORDER_SIDE_BUY"
,
"type"
:
"ORDER_TYPE_LIMIT"
,
"price"
: {
"value"
:
"0.55"
,
"currency"
:
"USD"
},
"quantity"
:
123
,
"cumQuantity"
:
123
,
"leavesQuantity"
:
123
,
"tif"
:
"TIME_IN_FORCE_DAY"
,
"goodTillTime"
:
"2023-11-07T05:31:56Z"
,
"intent"
:
"ORDER_INTENT_BUY_LONG"
,
"marketMetadata"
: {
"slug"
:
"<string>"
,
"icon"
:
"<string>"
,
"title"
:
"<string>"
,
"outcome"
:
"<string>"
,
"eventSlug"
:
"<string>"
,
"teamId"
:
123
,
"team"
: {
"id"
:
123
,
"name"
:
"<string>"
,
"abbreviation"
:
"<string>"
,
"league"
:
"<string>"
,
"record"
:
"<string>"
,
"logo"
:
"<string>"
,
"alias"
:
"<string>"
,
"safeName"
:
"<string>"
,
"homeIcon"
:
"<string>"
,
"awayIcon"
:
"<string>"
,
"colorPrimary"
:
"<string>"
,
"ordering"
:
"<string>"
,
"ranking"
:
"<string>"
,
"conference"
:
"<string>"
}
},
"state"
:
"ORDER_STATE_NEW"
,
"commissionNotionalTotalCollected"
: {
"value"
:
"0.55"
,
"currency"
:
"USD"
},
"commissionsBasisPoints"
:
"<string>"
,
"makerCommissionsBasisPoints"
:
"<string>"
,
"avgPx"
: {
"value"
:
"0.55"
,
"currency"
:
"USD"
},
"cashOrderQty"
: {
"value"
:
"0.55"
,
"currency"
:
"USD"
},
"insertTime"
:
"2023-11-07T05:31:56Z"
,
"createTime"
:
"2023-11-07T05:31:56Z"
,
"outcomeSide"
:
"OUTCOME_SIDE_YES"
,
"action"
:
"ORDER_ACTION_BUY"
}
]
}
GET
/
v1
/
orders
/
open
Try it
Get Open Orders
cURL
curl
--request
GET
\
--url
https://api.polymarket.us/v1/orders/open
\
--header
'X-PM-Access-Key: <api-key>'
\
--header
'X-PM-Signature: <api-key>'
\
--header
'X-PM-Timestamp: <api-key>'
import requests
url = "https://api.polymarket.us/v1/orders/open"
headers = {
"X-PM-Access-Key": "<api-key>",
"X-PM-Timestamp": "<api-key>",
"X-PM-Signature": "<api-key>"
}
response = requests.get(url, headers=headers)
print(response.text)
const options = {
method: 'GET',
headers: {
'X-PM-Access-Key': '<api-key>',
'X-PM-Timestamp': '<api-key>',
'X-PM-Signature': '<api-key>'
}
};
fetch('https://api.polymarket.us/v1/orders/open', options)
.then(res => res.json())
.then(res => console.log(res))
.catch(err => console.error(err));
<?php
$curl = curl_init();
curl_setopt_array($curl, [
CURLOPT_URL => "https://api.polymarket.us/v1/orders/open",
CURLOPT_RETURNTRANSFER => true,
CURLOPT_ENCODING => "",
CURLOPT_MAXREDIRS => 10,
CURLOPT_TIMEOUT => 30,
CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
CURLOPT_CUSTOMREQUEST => "GET",
CURLOPT_HTTPHEADER => [
"X-PM-Access-Key: <api-key>",
"X-PM-Signature: <api-key>",
"X-PM-Timestamp: <api-key>"
],
]);
$response = curl_exec($curl);
$err = curl_error($curl);
curl_close($curl);
if ($err) {
echo "cURL Error #:" . $err;
} else {
echo $response;
}
package main
import (
"fmt"
"net/http"
"io"
)
func main() {
url := "https://api.polymarket.us/v1/orders/open"
req, _ := http.NewRequest("GET", url, nil)
req.Header.Add("X-PM-Access-Key", "<api-key>")
req.Header.Add("X-PM-Timestamp", "<api-key>")
req.Header.Add("X-PM-Signature", "<api-key>")
res, _ := http.DefaultClient.Do(req)
defer res.Body.Close()
body, _ := io.ReadAll(res.Body)
fmt.Println(string(body))
}
HttpResponse<String> response = Unirest.get("https://api.polymarket.us/v1/orders/open")
.header("X-PM-Access-Key", "<api-key>")
.header("X-PM-Timestamp", "<api-key>")
.header("X-PM-Signature", "<api-key>")
.asString();
require 'uri'
require 'net/http'
url = URI("https://api.polymarket.us/v1/orders/open")
http = Net::HTTP.new(url.host, url.port)
http.use_ssl = true
request = Net::HTTP::Get.new(url)
request["X-PM-Access-Key"] = '<api-key>'
request["X-PM-Timestamp"] = '<api-key>'
request["X-PM-Signature"] = '<api-key>'
response = http.request(request)
puts response.read_body
200
{
"orders"
: [
{
"id"
:
"<string>"
,
"marketSlug"
:
"<string>"
,
"side"
:
"ORDER_SIDE_BUY"
,
"type"
:
"ORDER_TYPE_LIMIT"
,
"price"
: {
"value"
:
"0.55"
,
"currency"
:
"USD"
},
"quantity"
:
123
,
"cumQuantity"
:
123
,
"leavesQuantity"
:
123
,
"tif"
:
"TIME_IN_FORCE_DAY"
,
"goodTillTime"
:
"2023-11-07T05:31:56Z"
,
"intent"
:
"ORDER_INTENT_BUY_LONG"
,
"marketMetadata"
: {
"slug"
:
"<string>"
,
"icon"
:
"<string>"
,
"title"
:
"<string>"
,
"outcome"
:
"<string>"
,
"eventSlug"
:
"<string>"
,
"teamId"
:
123
,
"team"
: {
"id"
:
123
,
"name"
:
"<string>"
,
"abbreviation"
:
"<string>"
,
"league"
:
"<string>"
,
"record"
:
"<string>"
,
"logo"
:
"<string>"
,
"alias"
:
"<string>"
,
"safeName"
:
"<string>"
,
"homeIcon"
:
"<string>"
,
"awayIcon"
:
"<string>"
,
"colorPrimary"
:
"<string>"
,
"ordering"
:
"<string>"
,
"ranking"
:
"<string>"
,
"conference"
:
"<string>"
}
},
"state"
:
"ORDER_STATE_NEW"
,
"commissionNotionalTotalCollected"
: {
"value"
:
"0.55"
,
"currency"
:
"USD"
},
"commissionsBasisPoints"
:
"<string>"
,
"makerCommissionsBasisPoints"
:
"<string>"
,
"avgPx"
: {
"value"
:
"0.55"
,
"currency"
:
"USD"
},
"cashOrderQty"
: {
"value"
:
"0.55"
,
"currency"
:
"USD"
},
"insertTime"
:
"2023-11-07T05:31:56Z"
,
"createTime"
:
"2023-11-07T05:31:56Z"
,
"outcomeSide"
:
"OUTCOME_SIDE_YES"
,
"action"
:
"ORDER_ACTION_BUY"
}
]
}
Authorizations
​
X-PM-Access-Key
string
header
required
Your API key ID (UUID). Generate at
polymarket.us/developer
.
​
X-PM-Timestamp
string
header
required
Unix timestamp in milliseconds. Must be within 30 seconds of server time.
​
X-PM-Signature
string
header
required
Base64-encoded Ed25519 signature of
timestamp + method + path
. See
Authentication
for details.
Query Parameters
​
slugs
string[]
List of market slugs to filter by. Pass multiple values to filter by multiple markets (e.g.,
?slugs=market-1&slugs=market-2
)
Response
200
application/json
List of open orders
Response containing list of open orders
​
orders
object[]
List of open orders
Show
child attributes
```

### Create Order (POST)
**Source Routing Target:** https://docs.polymarket.us/api-reference/orders/create-order

```text
Create Order
cURL
curl
--request
POST
\
--url
https://api.polymarket.us/v1/orders
\
--header
'Content-Type: application/json'
\
--header
'X-PM-Access-Key: <api-key>'
\
--header
'X-PM-Signature: <api-key>'
\
--header
'X-PM-Timestamp: <api-key>'
\
--data
'
{
"marketSlug": "<string>",
"quantity": 123,
"participateDontInitiate": true,
"goodTillTime": "<string>",
"synchronousExecution": true,
"maxBlockTime": "<string>",
"slippageTolerance": {
"bips": 123,
"ticks": 123
}
}
'
import requests
url = "https://api.polymarket.us/v1/orders"
payload = {
"marketSlug": "<string>",
"quantity": 123,
"participateDontInitiate": True,
"goodTillTime": "<string>",
"synchronousExecution": True,
"maxBlockTime": "<string>",
"slippageTolerance": {
"bips": 123,
"ticks": 123
}
}
headers = {
"X-PM-Access-Key": "<api-key>",
"X-PM-Timestamp": "<api-key>",
"X-PM-Signature": "<api-key>",
"Content-Type": "application/json"
}
response = requests.post(url, json=payload, headers=headers)
print(response.text)
const options = {
method: 'POST',
headers: {
'X-PM-Access-Key': '<api-key>',
'X-PM-Timestamp': '<api-key>',
'X-PM-Signature': '<api-key>',
'Content-Type': 'application/json'
},
body: JSON.stringify({
marketSlug: '<string>',
quantity: 123,
participateDontInitiate: true,
goodTillTime: '<string>',
synchronousExecution: true,
maxBlockTime: '<string>',
slippageTolerance: {bips: 123, ticks: 123}
})
};
fetch('https://api.polymarket.us/v1/orders', options)
.then(res => res.json())
.then(res => console.log(res))
.catch(err => console.error(err));
<?php
$curl = curl_init();
curl_setopt_array($curl, [
CURLOPT_URL => "https://api.polymarket.us/v1/orders",
CURLOPT_RETURNTRANSFER => true,
CURLOPT_ENCODING => "",
CURLOPT_MAXREDIRS => 10,
CURLOPT_TIMEOUT => 30,
CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
CURLOPT_CUSTOMREQUEST => "POST",
CURLOPT_POSTFIELDS => json_encode([
'marketSlug' => '<string>',
'quantity' => 123,
'participateDontInitiate' => true,
'goodTillTime' => '<string>',
'synchronousExecution' => true,
'maxBlockTime' => '<string>',
'slippageTolerance' => [
'bips' => 123,
'ticks' => 123
]
]),
CURLOPT_HTTPHEADER => [
"Content-Type: application/json",
"X-PM-Access-Key: <api-key>",
"X-PM-Signature: <api-key>",
"X-PM-Timestamp: <api-key>"
],
]);
$response = curl_exec($curl);
$err = curl_error($curl);
curl_close($curl);
if ($err) {
echo "cURL Error #:" . $err;
} else {
echo $response;
}
package main
import (
"fmt"
"strings"
"net/http"
"io"
)
func main() {
url := "https://api.polymarket.us/v1/orders"
payload := strings.NewReader("{\n \"marketSlug\": \"<string>\",\n \"quantity\": 123,\n \"participateDontInitiate\": true,\n \"goodTillTime\": \"<string>\",\n \"synchronousExecution\": true,\n \"maxBlockTime\": \"<string>\",\n \"slippageTolerance\": {\n \"bips\": 123,\n \"ticks\": 123\n }\n}")
req, _ := http.NewRequest("POST", url, payload)
req.Header.Add("X-PM-Access-Key", "<api-key>")
req.Header.Add("X-PM-Timestamp", "<api-key>")
req.Header.Add("X-PM-Signature", "<api-key>")
req.Header.Add("Content-Type", "application/json")
res, _ := http.DefaultClient.Do(req)
defer res.Body.Close()
body, _ := io.ReadAll(res.Body)
fmt.Println(string(body))
}
HttpResponse<String> response = Unirest.post("https://api.polymarket.us/v1/orders")
.header("X-PM-Access-Key", "<api-key>")
.header("X-PM-Timestamp", "<api-key>")
.header("X-PM-Signature", "<api-key>")
.header("Content-Type", "application/json")
.body("{\n \"marketSlug\": \"<string>\",\n \"quantity\": 123,\n \"participateDontInitiate\": true,\n \"goodTillTime\": \"<string>\",\n \"synchronousExecution\": true,\n \"maxBlockTime\": \"<string>\",\n \"slippageTolerance\": {\n \"bips\": 123,\n \"ticks\": 123\n }\n}")
.asString();
require 'uri'
require 'net/http'
url = URI("https://api.polymarket.us/v1/orders")
http = Net::HTTP.new(url.host, url.port)
http.use_ssl = true
request = Net::HTTP::Post.new(url)
request["X-PM-Access-Key"] = '<api-key>'
request["X-PM-Timestamp"] = '<api-key>'
request["X-PM-Signature"] = '<api-key>'
request["Content-Type"] = 'application/json'
request.body = "{\n \"marketSlug\": \"<string>\",\n \"quantity\": 123,\n \"participateDontInitiate\": true,\n \"goodTillTime\": \"<string>\",\n \"synchronousExecution\": true,\n \"maxBlockTime\": \"<string>\",\n \"slippageTolerance\": {\n \"bips\": 123,\n \"ticks\": 123\n }\n}"
response = http.request(request)
puts response.read_body
200
{
"id"
:
"<string>"
,
"executions"
: [
{
"id"
:
"<string>"
,
"order"
: {
"id"
:
"<string>"
,
"marketSlug"
:
"<string>"
,
"side"
:
"ORDER_SIDE_BUY"
,
"type"
:
"ORDER_TYPE_LIMIT"
,
"price"
: {
"value"
:
"0.55"
,
"currency"
:
"USD"
},
"quantity"
:
123
,
"cumQuantity"
:
123
,
"leavesQuantity"
:
123
,
"tif"
:
"TIME_IN_FORCE_DAY"
,
"goodTillTime"
:
"2023-11-07T05:31:56Z"
,
"intent"
:
"ORDER_INTENT_BUY_LONG"
,
"marketMetadata"
: {
"slug"
:
"<string>"
,
"icon"
:
"<string>"
,
"title"
:
"<string>"
,
"outcome"
:
"<string>"
,
"eventSlug"
:
"<string>"
,
"teamId"
:
123
,
"team"
: {
"id"
:
123
,
"name"
:
"<string>"
,
"abbreviation"
:
"<string>"
,
"league"
:
"<string>"
,
"record"
:
"<string>"
,
"logo"
:
"<string>"
,
"alias"
:
"<string>"
,
"safeName"
:
"<string>"
,
"homeIcon"
:
"<string>"
,
"awayIcon"
:
"<string>"
,
"colorPrimary"
:
"<string>"
,
"ordering"
:
"<string>"
,
"ranking"
:
"<string>"
,
"conference"
:
"<string>"
}
},
"state"
:
"ORDER_STATE_NEW"
,
"commissionNotionalTotalCollected"
: {
"value"
:
"0.55"
,
"currency"
:
"USD"
},
"commissionsBasisPoints"
:
"<string>"
,
"makerCommissionsBasisPoints"
:
"<string>"
,
"avgPx"
: {
"value"
:
"0.55"
,
"currency"
:
"USD"
},
"cashOrderQty"
: {
"value"
:
"0.55"
,
"currency"
:
"USD"
},
"insertTime"
:
"2023-11-07T05:31:56Z"
,
"createTime"
:
"2023-11-07T05:31:56Z"
,
"outcomeSide"
:
"OUTCOME_SIDE_YES"
,
"action"
:
"ORDER_ACTION_BUY"
},
"lastShares"
:
"<string>"
,
"lastPx"
: {
"value"
:
"0.55"
,
"currency"
:
"USD"
},
"type"
:
"EXECUTION_TYPE_NEW"
,
"text"
:
"<string>"
,
"orderRejectReason"
:
"ORD_REJECT_REASON_EXCHANGE_OPTION"
,
"transactTime"
:
"2023-11-07T05:31:56Z"
,
"legPrices"
: [
{
"marketSlug"
:
"<string>"
,
"anchor"
:
true
,
"px"
: {
"value"
:
"0.55"
,
"currency"
:
"USD"
},
"qty"
:
"<string>"
,
"side"
:
"ORDER_SIDE_BUY"
,
"referencePx"
:
"<string>"
}
],
"tradeId"
:
"<string>"
,
"aggressor"
:
true
,
"commissionNotionalCollected"
: {
"value"
:
"0.55"
,
"currency"
:
"USD"
},
"unsolicitedCancelReason"
:
"UNSOLICITED_CXL_REASON_CONNECTION_LOSS"
,
"traceId"
:
"<string>"
,
"commissionSpreadPx"
: {
"value"
:
"0.55"
,
"currency"
:
"USD"
},
"transactTradeDate"
:
"2023-11-07T05:31:56Z"
}
]
}
POST
/
v1
/
orders
Try it
Create Order
cURL
curl
--request
POST
\
--url
https://api.polymarket.us/v1/orders
\
--header
'Content-Type: application/json'
\
--header
'X-PM-Access-Key: <api-key>'
\
--header
'X-PM-Signature: <api-key>'
\
--header
'X-PM-Timestamp: <api-key>'
\
--data
'
{
"marketSlug": "<string>",
"quantity": 123,
"participateDontInitiate": true,
"goodTillTime": "<string>",
"synchronousExecution": true,
"maxBlockTime": "<string>",
"slippageTolerance": {
"bips": 123,
"ticks": 123
}
}
'
import requests
url = "https://api.polymarket.us/v1/orders"
payload = {
"marketSlug": "<string>",
"quantity": 123,
"participateDontInitiate": True,
"goodTillTime": "<string>",
"synchronousExecution": True,
"maxBlockTime": "<string>",
"slippageTolerance": {
"bips": 123,
"ticks": 123
}
}
headers = {
"X-PM-Access-Key": "<api-key>",
"X-PM-Timestamp": "<api-key>",
"X-PM-Signature": "<api-key>",
"Content-Type": "application/json"
}
response = requests.post(url, json=payload, headers=headers)
print(response.text)
const options = {
method: 'POST',
headers: {
'X-PM-Access-Key': '<api-key>',
'X-PM-Timestamp': '<api-key>',
'X-PM-Signature': '<api-key>',
'Content-Type': 'application/json'
},
body: JSON.stringify({
marketSlug: '<string>',
quantity: 123,
participateDontInitiate: true,
goodTillTime: '<string>',
synchronousExecution: true,
maxBlockTime: '<string>',
slippageTolerance: {bips: 123, ticks: 123}
})
};
fetch('https://api.polymarket.us/v1/orders', options)
.then(res => res.json())
.then(res => console.log(res))
.catch(err => console.error(err));
<?php
$curl = curl_init();
curl_setopt_array($curl, [
CURLOPT_URL => "https://api.polymarket.us/v1/orders",
CURLOPT_RETURNTRANSFER => true,
CURLOPT_ENCODING => "",
CURLOPT_MAXREDIRS => 10,
CURLOPT_TIMEOUT => 30,
CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
CURLOPT_CUSTOMREQUEST => "POST",
CURLOPT_POSTFIELDS => json_encode([
'marketSlug' => '<string>',
'quantity' => 123,
'participateDontInitiate' => true,
'goodTillTime' => '<string>',
'synchronousExecution' => true,
'maxBlockTime' => '<string>',
'slippageTolerance' => [
'bips' => 123,
'ticks' => 123
]
]),
CURLOPT_HTTPHEADER => [
"Content-Type: application/json",
"X-PM-Access-Key: <api-key>",
"X-PM-Signature: <api-key>",
"X-PM-Timestamp: <api-key>"
],
]);
$response = curl_exec($curl);
$err = curl_error($curl);
curl_close($curl);
if ($err) {
echo "cURL Error #:" . $err;
} else {
echo $response;
}
package main
import (
"fmt"
"strings"
"net/http"
"io"
)
func main() {
url := "https://api.polymarket.us/v1/orders"
payload := strings.NewReader("{\n \"marketSlug\": \"<string>\",\n \"quantity\": 123,\n \"participateDontInitiate\": true,\n \"goodTillTime\": \"<string>\",\n \"synchronousExecution\": true,\n \"maxBlockTime\": \"<string>\",\n \"slippageTolerance\": {\n \"bips\": 123,\n \"ticks\": 123\n }\n}")
req, _ := http.NewRequest("POST", url, payload)
req.Header.Add("X-PM-Access-Key", "<api-key>")
req.Header.Add("X-PM-Timestamp", "<api-key>")
req.Header.Add("X-PM-Signature", "<api-key>")
req.Header.Add("Content-Type", "application/json")
res, _ := http.DefaultClient.Do(req)
defer res.Body.Close()
body, _ := io.ReadAll(res.Body)
fmt.Println(string(body))
}
HttpResponse<String> response = Unirest.post("https://api.polymarket.us/v1/orders")
.header("X-PM-Access-Key", "<api-key>")
.header("X-PM-Timestamp", "<api-key>")
.header("X-PM-Signature", "<api-key>")
.header("Content-Type", "application/json")
.body("{\n \"marketSlug\": \"<string>\",\n \"quantity\": 123,\n \"participateDontInitiate\": true,\n \"goodTillTime\": \"<string>\",\n \"synchronousExecution\": true,\n \"maxBlockTime\": \"<string>\",\n \"slippageTolerance\": {\n \"bips\": 123,\n \"ticks\": 123\n }\n}")
.asString();
require 'uri'
require 'net/http'
url = URI("https://api.polymarket.us/v1/orders")
http = Net::HTTP.new(url.host, url.port)
http.use_ssl = true
request = Net::HTTP::Post.new(url)
request["X-PM-Access-Key"] = '<api-key>'
request["X-PM-Timestamp"] = '<api-key>'
request["X-PM-Signature"] = '<api-key>'
request["Content-Type"] = 'application/json'
request.body = "{\n \"marketSlug\": \"<string>\",\n \"quantity\": 123,\n \"participateDontInitiate\": true,\n \"goodTillTime\": \"<string>\",\n \"synchronousExecution\": true,\n \"maxBlockTime\": \"<string>\",\n \"slippageTolerance\": {\n \"bips\": 123,\n \"ticks\": 123\n }\n}"
response = http.request(request)
puts response.read_body
200
{
"id"
:
"<string>"
,
"executions"
: [
{
"id"
:
"<string>"
,
"order"
: {
"id"
:
"<string>"
,
"marketSlug"
:
"<string>"
,
"side"
:
"ORDER_SIDE_BUY"
,
"type"
:
"ORDER_TYPE_LIMIT"
,
"price"
: {
"value"
:
"0.55"
,
"currency"
:
"USD"
},
"quantity"
:
123
,
"cumQuantity"
:
123
,
"leavesQuantity"
:
123
,
"tif"
:
"TIME_IN_FORCE_DAY"
,
"goodTillTime"
:
"2023-11-07T05:31:56Z"
,
"intent"
:
"ORDER_INTENT_BUY_LONG"
,
"marketMetadata"
: {
"slug"
:
"<string>"
,
"icon"
:
"<string>"
,
"title"
:
"<string>"
,
"outcome"
:
"<string>"
,
"eventSlug"
:
"<string>"
,
"teamId"
:
123
,
"team"
: {
"id"
:
123
,
"name"
:
"<string>"
,
"abbreviation"
:
"<string>"
,
"league"
:
"<string>"
,
"record"
:
"<string>"
,
"logo"
:
"<string>"
,
"alias"
:
"<string>"
,
"safeName"
:
"<string>"
,
"homeIcon"
:
"<string>"
,
"awayIcon"
:
"<string>"
,
"colorPrimary"
:
"<string>"
,
"ordering"
:
"<string>"
,
"ranking"
:
"<string>"
,
"conference"
:
"<string>"
}
},
"state"
:
"ORDER_STATE_NEW"
,
"commissionNotionalTotalCollected"
: {
"value"
:
"0.55"
,
"currency"
:
"USD"
},
"commissionsBasisPoints"
:
"<string>"
,
"makerCommissionsBasisPoints"
:
"<string>"
,
"avgPx"
: {
"value"
:
"0.55"
,
"currency"
:
"USD"
},
"cashOrderQty"
: {
"value"
:
"0.55"
,
"currency"
:
"USD"
},
"insertTime"
:
"2023-11-07T05:31:56Z"
,
"createTime"
:
"2023-11-07T05:31:56Z"
,
"outcomeSide"
:
"OUTCOME_SIDE_YES"
,
"action"
:
"ORDER_ACTION_BUY"
},
"lastShares"
:
"<string>"
,
"lastPx"
: {
"value"
:
"0.55"
,
"currency"
:
"USD"
},
"type"
:
"EXECUTION_TYPE_NEW"
,
"text"
:
"<string>"
,
"orderRejectReason"
:
"ORD_REJECT_REASON_EXCHANGE_OPTION"
,
"transactTime"
:
"2023-11-07T05:31:56Z"
,
"legPrices"
: [
{
"marketSlug"
:
"<string>"
,
"anchor"
:
true
,
"px"
: {
"value"
:
"0.55"
,
"currency"
:
"USD"
},
"qty"
:
"<string>"
,
"side"
:
"ORDER_SIDE_BUY"
,
"referencePx"
:
"<string>"
}
],
"tradeId"
:
"<string>"
,
"aggressor"
:
true
,
"commissionNotionalCollected"
: {
"value"
:
"0.55"
,
"currency"
:
"USD"
},
"unsolicitedCancelReason"
:
"UNSOLICITED_CXL_REASON_CONNECTION_LOSS"
,
"traceId"
:
"<string>"
,
"commissionSpreadPx"
: {
"value"
:
"0.55"
,
"currency"
:
"USD"
},
"transactTradeDate"
:
"2023-11-07T05:31:56Z"
}
]
}
Authorizations
​
X-PM-Access-Key
string
header
required
Your API key ID (UUID). Generate at
polymarket.us/developer
.
​
X-PM-Timestamp
string
header
required
Unix timestamp in milliseconds. Must be within 30 seconds of server time.
​
X-PM-Signature
string
header
required
Base64-encoded Ed25519 signature of
timestamp + method + path
. See
Authentication
for details.
Body
application/json
Request to create a new order
Request to create a new order.
​
marketSlug
string
required
Unique market slug into which the order should be entered
​
type
enum<string>
Type of order (limit or market)
Available options
:
ORDER_TYPE_LIMIT
,
ORDER_TYPE_MARKET
​
price
object
Order price and currency. Required for limit orders.
Show
child attributes
​
quantity
number<double>
Order quantity in contracts. Supports decimal quantities on markets whose minimumTradeQty is less than 1.
​
tif
enum<string>
Order time in force policy
Available options
:
TIME_IN_FORCE_DAY
,
TIME_IN_FORCE_GOOD_TILL_CANCEL
,
TIME_IN_FORCE_GOOD_TILL_DATE
,
TIME_IN_FORCE_IMMEDIATE_OR_CANCEL
,
TIME_IN_FORCE_FILL_OR_KILL
​
participateDontInitiate
boolean
If true, order must rest on the book prior to matching (maker only). Order will be rejected if it would immediately match.
​
goodTillTime
string
Expiration time for orders with TIME_IN_FORCE_GOOD_TILL_DATE
​
intent
enum<string>
Order intent. Either
intent
or (
outcomeSide
+
action
) must be set.
Available options
:
ORDER_INTENT_BUY_LONG
,
ORDER_INTENT_SELL_LONG
,
ORDER_INTENT_BUY_SHORT
,
ORDER_INTENT_SELL_SHORT
​
outcomeSide
enum<string>
Outcome side. Set with
action
as an alternative to
intent
. Takes priority if both are set.
Available options
:
OUTCOME_SIDE_YES
,
OUTCOME_SIDE_NO
​
action
enum<string>
Order action. Set with
outcomeSide
as an alternative to
intent
.
Available options
:
ORDER_ACTION_BUY
,
ORDER_ACTION_SELL
​
cashOrderQty
object
Order quantity in cash and currency. Used for market orders instead of share quantity.
Show
child attributes
​
manualOrderIndicator
enum<string>
Indicates whether the order was placed manually or automatically
Available options
:
MANUAL_ORDER_INDICATOR_MANUAL
,
MANUAL_ORDER_INDICATOR_AUTOMATIC
​
synchronousExecution
boolean
If true, will block until the order is filled, rejected, canceled, or expired, up to maxBlockTime seconds
​
maxBlockTime
string<int64>
Maximum block time in seconds if synchronous execution is requested
​
slippageTolerance
object
Slippage tolerance configuration for the order
Show
child attributes
Response
200
application/json
Order created successfully
Response containing created order ID
​
id
string
Exchange-assigned order ID
​
executions
object[]
Executions if synchronous execution was requested
Show
child attributes
```

### Cancel All Open Orders (POST)
**Source Routing Target:** https://docs.polymarket.us/api-reference/orders/cancel-all

```text
ERROR: Status code 404
```

### Cancel Order (POST)
**Source Routing Target:** https://docs.polymarket.us/api-reference/orders/cancel-order

```text
Cancel Order
cURL
curl
--request
POST
\
--url
https://api.polymarket.us/v1/order/{orderId}/cancel
\
--header
'Content-Type: application/json'
\
--header
'X-PM-Access-Key: <api-key>'
\
--header
'X-PM-Signature: <api-key>'
\
--header
'X-PM-Timestamp: <api-key>'
\
--data
'
{
"marketSlug": "<string>"
}
'
import requests
url = "https://api.polymarket.us/v1/order/{orderId}/cancel"
payload = { "marketSlug": "<string>" }
headers = {
"X-PM-Access-Key": "<api-key>",
"X-PM-Timestamp": "<api-key>",
"X-PM-Signature": "<api-key>",
"Content-Type": "application/json"
}
response = requests.post(url, json=payload, headers=headers)
print(response.text)
const options = {
method: 'POST',
headers: {
'X-PM-Access-Key': '<api-key>',
'X-PM-Timestamp': '<api-key>',
'X-PM-Signature': '<api-key>',
'Content-Type': 'application/json'
},
body: JSON.stringify({marketSlug: '<string>'})
};
fetch('https://api.polymarket.us/v1/order/{orderId}/cancel', options)
.then(res => res.json())
.then(res => console.log(res))
.catch(err => console.error(err));
<?php
$curl = curl_init();
curl_setopt_array($curl, [
CURLOPT_URL => "https://api.polymarket.us/v1/order/{orderId}/cancel",
CURLOPT_RETURNTRANSFER => true,
CURLOPT_ENCODING => "",
CURLOPT_MAXREDIRS => 10,
CURLOPT_TIMEOUT => 30,
CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
CURLOPT_CUSTOMREQUEST => "POST",
CURLOPT_POSTFIELDS => json_encode([
'marketSlug' => '<string>'
]),
CURLOPT_HTTPHEADER => [
"Content-Type: application/json",
"X-PM-Access-Key: <api-key>",
"X-PM-Signature: <api-key>",
"X-PM-Timestamp: <api-key>"
],
]);
$response = curl_exec($curl);
$err = curl_error($curl);
curl_close($curl);
if ($err) {
echo "cURL Error #:" . $err;
} else {
echo $response;
}
package main
import (
"fmt"
"strings"
"net/http"
"io"
)
func main() {
url := "https://api.polymarket.us/v1/order/{orderId}/cancel"
payload := strings.NewReader("{\n \"marketSlug\": \"<string>\"\n}")
req, _ := http.NewRequest("POST", url, payload)
req.Header.Add("X-PM-Access-Key", "<api-key>")
req.Header.Add("X-PM-Timestamp", "<api-key>")
req.Header.Add("X-PM-Signature", "<api-key>")
req.Header.Add("Content-Type", "application/json")
res, _ := http.DefaultClient.Do(req)
defer res.Body.Close()
body, _ := io.ReadAll(res.Body)
fmt.Println(string(body))
}
HttpResponse<String> response = Unirest.post("https://api.polymarket.us/v1/order/{orderId}/cancel")
.header("X-PM-Access-Key", "<api-key>")
.header("X-PM-Timestamp", "<api-key>")
.header("X-PM-Signature", "<api-key>")
.header("Content-Type", "application/json")
.body("{\n \"marketSlug\": \"<string>\"\n}")
.asString();
require 'uri'
require 'net/http'
url = URI("https://api.polymarket.us/v1/order/{orderId}/cancel")
http = Net::HTTP.new(url.host, url.port)
http.use_ssl = true
request = Net::HTTP::Post.new(url)
request["X-PM-Access-Key"] = '<api-key>'
request["X-PM-Timestamp"] = '<api-key>'
request["X-PM-Signature"] = '<api-key>'
request["Content-Type"] = 'application/json'
request.body = "{\n \"marketSlug\": \"<string>\"\n}"
response = http.request(request)
puts response.read_body
200
{}
POST
/
v1
/
order
/
{orderId}
/
cancel
Try it
Cancel Order
cURL
curl
--request
POST
\
--url
https://api.polymarket.us/v1/order/{orderId}/cancel
\
--header
'Content-Type: application/json'
\
--header
'X-PM-Access-Key: <api-key>'
\
--header
'X-PM-Signature: <api-key>'
\
--header
'X-PM-Timestamp: <api-key>'
\
--data
'
{
"marketSlug": "<string>"
}
'
import requests
url = "https://api.polymarket.us/v1/order/{orderId}/cancel"
payload = { "marketSlug": "<string>" }
headers = {
"X-PM-Access-Key": "<api-key>",
"X-PM-Timestamp": "<api-key>",
"X-PM-Signature": "<api-key>",
"Content-Type": "application/json"
}
response = requests.post(url, json=payload, headers=headers)
print(response.text)
const options = {
method: 'POST',
headers: {
'X-PM-Access-Key': '<api-key>',
'X-PM-Timestamp': '<api-key>',
'X-PM-Signature': '<api-key>',
'Content-Type': 'application/json'
},
body: JSON.stringify({marketSlug: '<string>'})
};
fetch('https://api.polymarket.us/v1/order/{orderId}/cancel', options)
.then(res => res.json())
.then(res => console.log(res))
.catch(err => console.error(err));
<?php
$curl = curl_init();
curl_setopt_array($curl, [
CURLOPT_URL => "https://api.polymarket.us/v1/order/{orderId}/cancel",
CURLOPT_RETURNTRANSFER => true,
CURLOPT_ENCODING => "",
CURLOPT_MAXREDIRS => 10,
CURLOPT_TIMEOUT => 30,
CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
CURLOPT_CUSTOMREQUEST => "POST",
CURLOPT_POSTFIELDS => json_encode([
'marketSlug' => '<string>'
]),
CURLOPT_HTTPHEADER => [
"Content-Type: application/json",
"X-PM-Access-Key: <api-key>",
"X-PM-Signature: <api-key>",
"X-PM-Timestamp: <api-key>"
],
]);
$response = curl_exec($curl);
$err = curl_error($curl);
curl_close($curl);
if ($err) {
echo "cURL Error #:" . $err;
} else {
echo $response;
}
package main
import (
"fmt"
"strings"
"net/http"
"io"
)
func main() {
url := "https://api.polymarket.us/v1/order/{orderId}/cancel"
payload := strings.NewReader("{\n \"marketSlug\": \"<string>\"\n}")
req, _ := http.NewRequest("POST", url, payload)
req.Header.Add("X-PM-Access-Key", "<api-key>")
req.Header.Add("X-PM-Timestamp", "<api-key>")
req.Header.Add("X-PM-Signature", "<api-key>")
req.Header.Add("Content-Type", "application/json")
res, _ := http.DefaultClient.Do(req)
defer res.Body.Close()
body, _ := io.ReadAll(res.Body)
fmt.Println(string(body))
}
HttpResponse<String> response = Unirest.post("https://api.polymarket.us/v1/order/{orderId}/cancel")
.header("X-PM-Access-Key", "<api-key>")
.header("X-PM-Timestamp", "<api-key>")
.header("X-PM-Signature", "<api-key>")
.header("Content-Type", "application/json")
.body("{\n \"marketSlug\": \"<string>\"\n}")
.asString();
require 'uri'
require 'net/http'
url = URI("https://api.polymarket.us/v1/order/{orderId}/cancel")
http = Net::HTTP.new(url.host, url.port)
http.use_ssl = true
request = Net::HTTP::Post.new(url)
request["X-PM-Access-Key"] = '<api-key>'
request["X-PM-Timestamp"] = '<api-key>'
request["X-PM-Signature"] = '<api-key>'
request["Content-Type"] = 'application/json'
request.body = "{\n \"marketSlug\": \"<string>\"\n}"
response = http.request(request)
puts response.read_body
200
{}
Authorizations
​
X-PM-Access-Key
string
header
required
Your API key ID (UUID). Generate at
polymarket.us/developer
.
​
X-PM-Timestamp
string
header
required
Unix timestamp in milliseconds. Must be within 30 seconds of server time.
​
X-PM-Signature
string
header
required
Base64-encoded Ed25519 signature of
timestamp + method + path
. See
Authentication
for details.
Path Parameters
​
orderId
string
required
Exchange-assigned Order ID to cancel
Body
application/json
Request to cancel an existing order
Request to cancel an existing order
​
marketSlug
string
Unique market slug into which the order should be canceled
Response
200
application/json
Order canceled successfully
Response for order cancellation (empty on success)
```

### Modify Order (POST)
**Source Routing Target:** https://docs.polymarket.us/api-reference/orders/modify-order

```text
Modify Order
cURL
curl
--request
POST
\
--url
https://api.polymarket.us/v1/order/{orderId}/modify
\
--header
'Content-Type: application/json'
\
--header
'X-PM-Access-Key: <api-key>'
\
--header
'X-PM-Signature: <api-key>'
\
--header
'X-PM-Timestamp: <api-key>'
\
--data
'
{
"marketSlug": "<string>",
"quantity": 123,
"participateDontInitiate": true,
"goodTillTime": "<string>"
}
'
import requests
url = "https://api.polymarket.us/v1/order/{orderId}/modify"
payload = {
"marketSlug": "<string>",
"quantity": 123,
"participateDontInitiate": True,
"goodTillTime": "<string>"
}
headers = {
"X-PM-Access-Key": "<api-key>",
"X-PM-Timestamp": "<api-key>",
"X-PM-Signature": "<api-key>",
"Content-Type": "application/json"
}
response = requests.post(url, json=payload, headers=headers)
print(response.text)
const options = {
method: 'POST',
headers: {
'X-PM-Access-Key': '<api-key>',
'X-PM-Timestamp': '<api-key>',
'X-PM-Signature': '<api-key>',
'Content-Type': 'application/json'
},
body: JSON.stringify({
marketSlug: '<string>',
quantity: 123,
participateDontInitiate: true,
goodTillTime: '<string>'
})
};
fetch('https://api.polymarket.us/v1/order/{orderId}/modify', options)
.then(res => res.json())
.then(res => console.log(res))
.catch(err => console.error(err));
<?php
$curl = curl_init();
curl_setopt_array($curl, [
CURLOPT_URL => "https://api.polymarket.us/v1/order/{orderId}/modify",
CURLOPT_RETURNTRANSFER => true,
CURLOPT_ENCODING => "",
CURLOPT_MAXREDIRS => 10,
CURLOPT_TIMEOUT => 30,
CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
CURLOPT_CUSTOMREQUEST => "POST",
CURLOPT_POSTFIELDS => json_encode([
'marketSlug' => '<string>',
'quantity' => 123,
'participateDontInitiate' => true,
'goodTillTime' => '<string>'
]),
CURLOPT_HTTPHEADER => [
"Content-Type: application/json",
"X-PM-Access-Key: <api-key>",
"X-PM-Signature: <api-key>",
"X-PM-Timestamp: <api-key>"
],
]);
$response = curl_exec($curl);
$err = curl_error($curl);
curl_close($curl);
if ($err) {
echo "cURL Error #:" . $err;
} else {
echo $response;
}
package main
import (
"fmt"
"strings"
"net/http"
"io"
)
func main() {
url := "https://api.polymarket.us/v1/order/{orderId}/modify"
payload := strings.NewReader("{\n \"marketSlug\": \"<string>\",\n \"quantity\": 123,\n \"participateDontInitiate\": true,\n \"goodTillTime\": \"<string>\"\n}")
req, _ := http.NewRequest("POST", url, payload)
req.Header.Add("X-PM-Access-Key", "<api-key>")
req.Header.Add("X-PM-Timestamp", "<api-key>")
req.Header.Add("X-PM-Signature", "<api-key>")
req.Header.Add("Content-Type", "application/json")
res, _ := http.DefaultClient.Do(req)
defer res.Body.Close()
body, _ := io.ReadAll(res.Body)
fmt.Println(string(body))
}
HttpResponse<String> response = Unirest.post("https://api.polymarket.us/v1/order/{orderId}/modify")
.header("X-PM-Access-Key", "<api-key>")
.header("X-PM-Timestamp", "<api-key>")
.header("X-PM-Signature", "<api-key>")
.header("Content-Type", "application/json")
.body("{\n \"marketSlug\": \"<string>\",\n \"quantity\": 123,\n \"participateDontInitiate\": true,\n \"goodTillTime\": \"<string>\"\n}")
.asString();
require 'uri'
require 'net/http'
url = URI("https://api.polymarket.us/v1/order/{orderId}/modify")
http = Net::HTTP.new(url.host, url.port)
http.use_ssl = true
request = Net::HTTP::Post.new(url)
request["X-PM-Access-Key"] = '<api-key>'
request["X-PM-Timestamp"] = '<api-key>'
request["X-PM-Signature"] = '<api-key>'
request["Content-Type"] = 'application/json'
request.body = "{\n \"marketSlug\": \"<string>\",\n \"quantity\": 123,\n \"participateDontInitiate\": true,\n \"goodTillTime\": \"<string>\"\n}"
response = http.request(request)
puts response.read_body
200
{}
POST
/
v1
/
order
/
{orderId}
/
modify
Try it
Modify Order
cURL
curl
--request
POST
\
--url
https://api.polymarket.us/v1/order/{orderId}/modify
\
--header
'Content-Type: application/json'
\
--header
'X-PM-Access-Key: <api-key>'
\
--header
'X-PM-Signature: <api-key>'
\
--header
'X-PM-Timestamp: <api-key>'
\
--data
'
{
"marketSlug": "<string>",
"quantity": 123,
"participateDontInitiate": true,
"goodTillTime": "<string>"
}
'
import requests
url = "https://api.polymarket.us/v1/order/{orderId}/modify"
payload = {
"marketSlug": "<string>",
"quantity": 123,
"participateDontInitiate": True,
"goodTillTime": "<string>"
}
headers = {
"X-PM-Access-Key": "<api-key>",
"X-PM-Timestamp": "<api-key>",
"X-PM-Signature": "<api-key>",
"Content-Type": "application/json"
}
response = requests.post(url, json=payload, headers=headers)
print(response.text)
const options = {
method: 'POST',
headers: {
'X-PM-Access-Key': '<api-key>',
'X-PM-Timestamp': '<api-key>',
'X-PM-Signature': '<api-key>',
'Content-Type': 'application/json'
},
body: JSON.stringify({
marketSlug: '<string>',
quantity: 123,
participateDontInitiate: true,
goodTillTime: '<string>'
})
};
fetch('https://api.polymarket.us/v1/order/{orderId}/modify', options)
.then(res => res.json())
.then(res => console.log(res))
.catch(err => console.error(err));
<?php
$curl = curl_init();
curl_setopt_array($curl, [
CURLOPT_URL => "https://api.polymarket.us/v1/order/{orderId}/modify",
CURLOPT_RETURNTRANSFER => true,
CURLOPT_ENCODING => "",
CURLOPT_MAXREDIRS => 10,
CURLOPT_TIMEOUT => 30,
CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
CURLOPT_CUSTOMREQUEST => "POST",
CURLOPT_POSTFIELDS => json_encode([
'marketSlug' => '<string>',
'quantity' => 123,
'participateDontInitiate' => true,
'goodTillTime' => '<string>'
]),
CURLOPT_HTTPHEADER => [
"Content-Type: application/json",
"X-PM-Access-Key: <api-key>",
"X-PM-Signature: <api-key>",
"X-PM-Timestamp: <api-key>"
],
]);
$response = curl_exec($curl);
$err = curl_error($curl);
curl_close($curl);
if ($err) {
echo "cURL Error #:" . $err;
} else {
echo $response;
}
package main
import (
"fmt"
"strings"
"net/http"
"io"
)
func main() {
url := "https://api.polymarket.us/v1/order/{orderId}/modify"
payload := strings.NewReader("{\n \"marketSlug\": \"<string>\",\n \"quantity\": 123,\n \"participateDontInitiate\": true,\n \"goodTillTime\": \"<string>\"\n}")
req, _ := http.NewRequest("POST", url, payload)
req.Header.Add("X-PM-Access-Key", "<api-key>")
req.Header.Add("X-PM-Timestamp", "<api-key>")
req.Header.Add("X-PM-Signature", "<api-key>")
req.Header.Add("Content-Type", "application/json")
res, _ := http.DefaultClient.Do(req)
defer res.Body.Close()
body, _ := io.ReadAll(res.Body)
fmt.Println(string(body))
}
HttpResponse<String> response = Unirest.post("https://api.polymarket.us/v1/order/{orderId}/modify")
.header("X-PM-Access-Key", "<api-key>")
.header("X-PM-Timestamp", "<api-key>")
.header("X-PM-Signature", "<api-key>")
.header("Content-Type", "application/json")
.body("{\n \"marketSlug\": \"<string>\",\n \"quantity\": 123,\n \"participateDontInitiate\": true,\n \"goodTillTime\": \"<string>\"\n}")
.asString();
require 'uri'
require 'net/http'
url = URI("https://api.polymarket.us/v1/order/{orderId}/modify")
http = Net::HTTP.new(url.host, url.port)
http.use_ssl = true
request = Net::HTTP::Post.new(url)
request["X-PM-Access-Key"] = '<api-key>'
request["X-PM-Timestamp"] = '<api-key>'
request["X-PM-Signature"] = '<api-key>'
request["Content-Type"] = 'application/json'
request.body = "{\n \"marketSlug\": \"<string>\",\n \"quantity\": 123,\n \"participateDontInitiate\": true,\n \"goodTillTime\": \"<string>\"\n}"
response = http.request(request)
puts response.read_body
200
{}
Authorizations
​
X-PM-Access-Key
string
header
required
Your API key ID (UUID). Generate at
polymarket.us/developer
.
​
X-PM-Timestamp
string
header
required
Unix timestamp in milliseconds. Must be within 30 seconds of server time.
​
X-PM-Signature
string
header
required
Base64-encoded Ed25519 signature of
timestamp + method + path
. See
Authentication
for details.
Path Parameters
​
orderId
string
required
Exchange-assigned Order ID to modify
Body
application/json
Request to modify an existing order
Request to modify an existing order
​
marketSlug
string
Unique market slug for the order being modified
​
price
object
New order price and currency
Show
child attributes
​
quantity
number<double>
Order quantity in contracts. Supports decimal quantities on markets whose minimumTradeQty is less than 1.
​
tif
enum<string>
New order time in force
Available options
:
TIME_IN_FORCE_DAY
,
TIME_IN_FORCE_GOOD_TILL_CANCEL
,
TIME_IN_FORCE_GOOD_TILL_DATE
,
TIME_IN_FORCE_IMMEDIATE_OR_CANCEL
,
TIME_IN_FORCE_FILL_OR_KILL
​
participateDontInitiate
boolean
Order must rest on the book prior to matching (maker only)
​
goodTillTime
string
Good till time for orders with TIME_IN_FORCE_GOOD_TILL_DATE
Response
200
application/json
Order modified successfully
Response for order modification (empty on success)
```

### Preview Order (POST)
**Source Routing Target:** https://docs.polymarket.us/api-reference/orders/preview-order

```text
Preview Order
cURL
curl
--request
POST
\
--url
https://api.polymarket.us/v1/order/preview
\
--header
'Content-Type: application/json'
\
--header
'X-PM-Access-Key: <api-key>'
\
--header
'X-PM-Signature: <api-key>'
\
--header
'X-PM-Timestamp: <api-key>'
\
--data
'{}'
import requests
url = "https://api.polymarket.us/v1/order/preview"
payload = {}
headers = {
"X-PM-Access-Key": "<api-key>",
"X-PM-Timestamp": "<api-key>",
"X-PM-Signature": "<api-key>",
"Content-Type": "application/json"
}
response = requests.post(url, json=payload, headers=headers)
print(response.text)
const options = {
method: 'POST',
headers: {
'X-PM-Access-Key': '<api-key>',
'X-PM-Timestamp': '<api-key>',
'X-PM-Signature': '<api-key>',
'Content-Type': 'application/json'
},
body: JSON.stringify({})
};
fetch('https://api.polymarket.us/v1/order/preview', options)
.then(res => res.json())
.then(res => console.log(res))
.catch(err => console.error(err));
<?php
$curl = curl_init();
curl_setopt_array($curl, [
CURLOPT_URL => "https://api.polymarket.us/v1/order/preview",
CURLOPT_RETURNTRANSFER => true,
CURLOPT_ENCODING => "",
CURLOPT_MAXREDIRS => 10,
CURLOPT_TIMEOUT => 30,
CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
CURLOPT_CUSTOMREQUEST => "POST",
CURLOPT_POSTFIELDS => json_encode([
]),
CURLOPT_HTTPHEADER => [
"Content-Type: application/json",
"X-PM-Access-Key: <api-key>",
"X-PM-Signature: <api-key>",
"X-PM-Timestamp: <api-key>"
],
]);
$response = curl_exec($curl);
$err = curl_error($curl);
curl_close($curl);
if ($err) {
echo "cURL Error #:" . $err;
} else {
echo $response;
}
package main
import (
"fmt"
"strings"
"net/http"
"io"
)
func main() {
url := "https://api.polymarket.us/v1/order/preview"
payload := strings.NewReader("{}")
req, _ := http.NewRequest("POST", url, payload)
req.Header.Add("X-PM-Access-Key", "<api-key>")
req.Header.Add("X-PM-Timestamp", "<api-key>")
req.Header.Add("X-PM-Signature", "<api-key>")
req.Header.Add("Content-Type", "application/json")
res, _ := http.DefaultClient.Do(req)
defer res.Body.Close()
body, _ := io.ReadAll(res.Body)
fmt.Println(string(body))
}
HttpResponse<String> response = Unirest.post("https://api.polymarket.us/v1/order/preview")
.header("X-PM-Access-Key", "<api-key>")
.header("X-PM-Timestamp", "<api-key>")
.header("X-PM-Signature", "<api-key>")
.header("Content-Type", "application/json")
.body("{}")
.asString();
require 'uri'
require 'net/http'
url = URI("https://api.polymarket.us/v1/order/preview")
http = Net::HTTP.new(url.host, url.port)
http.use_ssl = true
request = Net::HTTP::Post.new(url)
request["X-PM-Access-Key"] = '<api-key>'
request["X-PM-Timestamp"] = '<api-key>'
request["X-PM-Signature"] = '<api-key>'
request["Content-Type"] = 'application/json'
request.body = "{}"
response = http.request(request)
puts response.read_body
200
{
"order"
: {
"id"
:
"<string>"
,
"marketSlug"
:
"<string>"
,
"side"
:
"ORDER_SIDE_BUY"
,
"type"
:
"ORDER_TYPE_LIMIT"
,
"price"
: {
"value"
:
"0.55"
,
"currency"
:
"USD"
},
"quantity"
:
123
,
"cumQuantity"
:
123
,
"leavesQuantity"
:
123
,
"tif"
:
"TIME_IN_FORCE_DAY"
,
"goodTillTime"
:
"2023-11-07T05:31:56Z"
,
"intent"
:
"ORDER_INTENT_BUY_LONG"
,
"marketMetadata"
: {
"slug"
:
"<string>"
,
"icon"
:
"<string>"
,
"title"
:
"<string>"
,
"outcome"
:
"<string>"
,
"eventSlug"
:
"<string>"
,
"teamId"
:
123
,
"team"
: {
"id"
:
123
,
"name"
:
"<string>"
,
"abbreviation"
:
"<string>"
,
"league"
:
"<string>"
,
"record"
:
"<string>"
,
"logo"
:
"<string>"
,
"alias"
:
"<string>"
,
"safeName"
:
"<string>"
,
"homeIcon"
:
"<string>"
,
"awayIcon"
:
"<string>"
,
"colorPrimary"
:
"<string>"
,
"ordering"
:
"<string>"
,
"ranking"
:
"<string>"
,
"conference"
:
"<string>"
}
},
"state"
:
"ORDER_STATE_NEW"
,
"commissionNotionalTotalCollected"
: {
"value"
:
"0.55"
,
"currency"
:
"USD"
},
"commissionsBasisPoints"
:
"<string>"
,
"makerCommissionsBasisPoints"
:
"<string>"
,
"avgPx"
: {
"value"
:
"0.55"
,
"currency"
:
"USD"
},
"cashOrderQty"
: {
"value"
:
"0.55"
,
"currency"
:
"USD"
},
"insertTime"
:
"2023-11-07T05:31:56Z"
,
"createTime"
:
"2023-11-07T05:31:56Z"
,
"outcomeSide"
:
"OUTCOME_SIDE_YES"
,
"action"
:
"ORDER_ACTION_BUY"
}
}
POST
/
v1
/
order
/
preview
Try it
Preview Order
cURL
curl
--request
POST
\
--url
https://api.polymarket.us/v1/order/preview
\
--header
'Content-Type: application/json'
\
--header
'X-PM-Access-Key: <api-key>'
\
--header
'X-PM-Signature: <api-key>'
\
--header
'X-PM-Timestamp: <api-key>'
\
--data
'{}'
import requests
url = "https://api.polymarket.us/v1/order/preview"
payload = {}
headers = {
"X-PM-Access-Key": "<api-key>",
"X-PM-Timestamp": "<api-key>",
"X-PM-Signature": "<api-key>",
"Content-Type": "application/json"
}
response = requests.post(url, json=payload, headers=headers)
print(response.text)
const options = {
method: 'POST',
headers: {
'X-PM-Access-Key': '<api-key>',
'X-PM-Timestamp': '<api-key>',
'X-PM-Signature': '<api-key>',
'Content-Type': 'application/json'
},
body: JSON.stringify({})
};
fetch('https://api.polymarket.us/v1/order/preview', options)
.then(res => res.json())
.then(res => console.log(res))
.catch(err => console.error(err));
<?php
$curl = curl_init();
curl_setopt_array($curl, [
CURLOPT_URL => "https://api.polymarket.us/v1/order/preview",
CURLOPT_RETURNTRANSFER => true,
CURLOPT_ENCODING => "",
CURLOPT_MAXREDIRS => 10,
CURLOPT_TIMEOUT => 30,
CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
CURLOPT_CUSTOMREQUEST => "POST",
CURLOPT_POSTFIELDS => json_encode([
]),
CURLOPT_HTTPHEADER => [
"Content-Type: application/json",
"X-PM-Access-Key: <api-key>",
"X-PM-Signature: <api-key>",
"X-PM-Timestamp: <api-key>"
],
]);
$response = curl_exec($curl);
$err = curl_error($curl);
curl_close($curl);
if ($err) {
echo "cURL Error #:" . $err;
} else {
echo $response;
}
package main
import (
"fmt"
"strings"
"net/http"
"io"
)
func main() {
url := "https://api.polymarket.us/v1/order/preview"
payload := strings.NewReader("{}")
req, _ := http.NewRequest("POST", url, payload)
req.Header.Add("X-PM-Access-Key", "<api-key>")
req.Header.Add("X-PM-Timestamp", "<api-key>")
req.Header.Add("X-PM-Signature", "<api-key>")
req.Header.Add("Content-Type", "application/json")
res, _ := http.DefaultClient.Do(req)
defer res.Body.Close()
body, _ := io.ReadAll(res.Body)
fmt.Println(string(body))
}
HttpResponse<String> response = Unirest.post("https://api.polymarket.us/v1/order/preview")
.header("X-PM-Access-Key", "<api-key>")
.header("X-PM-Timestamp", "<api-key>")
.header("X-PM-Signature", "<api-key>")
.header("Content-Type", "application/json")
.body("{}")
.asString();
require 'uri'
require 'net/http'
url = URI("https://api.polymarket.us/v1/order/preview")
http = Net::HTTP.new(url.host, url.port)
http.use_ssl = true
request = Net::HTTP::Post.new(url)
request["X-PM-Access-Key"] = '<api-key>'
request["X-PM-Timestamp"] = '<api-key>'
request["X-PM-Signature"] = '<api-key>'
request["Content-Type"] = 'application/json'
request.body = "{}"
response = http.request(request)
puts response.read_body
200
{
"order"
: {
"id"
:
"<string>"
,
"marketSlug"
:
"<string>"
,
"side"
:
"ORDER_SIDE_BUY"
,
"type"
:
"ORDER_TYPE_LIMIT"
,
"price"
: {
"value"
:
"0.55"
,
"currency"
:
"USD"
},
"quantity"
:
123
,
"cumQuantity"
:
123
,
"leavesQuantity"
:
123
,
"tif"
:
"TIME_IN_FORCE_DAY"
,
"goodTillTime"
:
"2023-11-07T05:31:56Z"
,
"intent"
:
"ORDER_INTENT_BUY_LONG"
,
"marketMetadata"
: {
"slug"
:
"<string>"
,
"icon"
:
"<string>"
,
"title"
:
"<string>"
,
"outcome"
:
"<string>"
,
"eventSlug"
:
"<string>"
,
"teamId"
:
123
,
"team"
: {
"id"
:
123
,
"name"
:
"<string>"
,
"abbreviation"
:
"<string>"
,
"league"
:
"<string>"
,
"record"
:
"<string>"
,
"logo"
:
"<string>"
,
"alias"
:
"<string>"
,
"safeName"
:
"<string>"
,
"homeIcon"
:
"<string>"
,
"awayIcon"
:
"<string>"
,
"colorPrimary"
:
"<string>"
,
"ordering"
:
"<string>"
,
"ranking"
:
"<string>"
,
"conference"
:
"<string>"
}
},
"state"
:
"ORDER_STATE_NEW"
,
"commissionNotionalTotalCollected"
: {
"value"
:
"0.55"
,
"currency"
:
"USD"
},
"commissionsBasisPoints"
:
"<string>"
,
"makerCommissionsBasisPoints"
:
"<string>"
,
"avgPx"
: {
"value"
:
"0.55"
,
"currency"
:
"USD"
},
"cashOrderQty"
: {
"value"
:
"0.55"
,
"currency"
:
"USD"
},
"insertTime"
:
"2023-11-07T05:31:56Z"
,
"createTime"
:
"2023-11-07T05:31:56Z"
,
"outcomeSide"
:
"OUTCOME_SIDE_YES"
,
"action"
:
"ORDER_ACTION_BUY"
}
}
Authorizations
​
X-PM-Access-Key
string
header
required
Your API key ID (UUID). Generate at
polymarket.us/developer
.
​
X-PM-Timestamp
string
header
required
Unix timestamp in milliseconds. Must be within 30 seconds of server time.
​
X-PM-Signature
string
header
required
Base64-encoded Ed25519 signature of
timestamp + method + path
. See
Authentication
for details.
Body
application/json
Request to preview an order
Request to preview an order
​
request
object
The order to preview
Show
child attributes
Response
200
application/json
Order previewed successfully
Response containing previewed order
​
order
object
Previewed order with calculated values
Show
child attributes
```

### Modify Multiple Orders (POST)
**Source Routing Target:** https://docs.polymarket.us/api-reference/orders/modify-multiple

```text
ERROR: Status code 404
```

### Create Multiple Orders (POST)
**Source Routing Target:** https://docs.polymarket.us/api-reference/orders/create-multiple

```text
ERROR: Status code 404
```

### Close Position Order (POST)
**Source Routing Target:** https://docs.polymarket.us/api-reference/orders/close-position

```text
ERROR: Status code 404
```

### Cancel Multiple Orders (POST)
**Source Routing Target:** https://docs.polymarket.us/api-reference/orders/cancel-multiple

```text
ERROR: Status code 404
```

## Section: Combos
---

### Combos API Overview
**Source Routing Target:** https://docs.polymarket.us/api-reference/combos/overview

```text
A combo is a user-defined instrument containing 2–10 legs. Each leg identifies an existing market symbol and whether the combo buys or sells that leg. Once open, a combo trades through the normal
Orders API
; an RFQ is optional and provides a price-discovery and paired order-submission workflow over the same order book.
All calls use normal
Retail API authentication
at:
https://api.polymarket.us
​
Endpoints
Method
Endpoint
Description
POST
/v1/combos
Create or retrieve the canonical combo for a set of legs
GET
/v1/combos?symbol={symbol}
Get a combo by exact symbol
On the Retail API, Combo and RFQ creation share an additional
edge rate limit
of 10 requests per 10 seconds, enforced per API key and per IP.
Separately, combo creation has a participant-wide service quota of 1,000 new instruments per week across all accounts and both Retail and Institutional APIs. The quota resets Monday at 00:00 UTC; returning an existing canonical combo does not consume it.
​
Create a Combo
POST /v1/combos
accepts 2–10 unique legs:
{
"legs"
: [
{
"symbol"
:
"market-a"
,
"side"
:
"SIDE_BUY"
},
{
"symbol"
:
"market-b"
,
"side"
:
"SIDE_SELL"
}
]
}
Leg symbols must be open, tradable, supported instruments. Duplicate symbols and invalid combinations are rejected. A canonical set of legs always maps to the same
caoc-...
combo symbol, so creating an existing combo returns that instrument.
{
"combo"
: {
"id"
:
"caoc-..."
,
"legs"
: [
{
"symbol"
:
"market-a"
,
"side"
:
"SIDE_BUY"
},
{
"symbol"
:
"market-b"
,
"side"
:
"SIDE_SELL"
}
],
"state"
:
"INSTRUMENT_STATE_OPEN"
,
"createdTime"
:
"2026-07-29T14:00:00Z"
,
"tickSize"
:
0.001
}
}
​
Get a Combo
GET /v1/combos?symbol=caoc-...
requires the exact combo symbol. The response contains a
combos
array; an unknown symbol returns an empty array. This endpoint does not paginate.
​
See Also
RFQ API
Create and manage combo RFQs and quotes
Authentication
Sign Retail API requests
Private WebSocket
Receive RFQ and quote lifecycle events
```

### Combos Endpoints
**Source Routing Target:** https://docs.polymarket.us/api-reference/combos/endpoints

```text
ERROR: Status code 404
```

## Section: RFQs
---

### RFQ API Overview
**Source Routing Target:** https://docs.polymarket.us/api-reference/rfqs/overview

```text
An RFQ requests two-sided liquidity for the exact symbol of a
combo instrument
. All calls use normal
Retail API authentication
at
https://api.polymarket.us
.
The Retail API derives the participant and account from the API key; clients do not send an account.
​
Endpoints
Method
Endpoint
Description
GET
/v1/rfqs/user-id
Get your pseudonymous RFQ user ID
GET
/v1/rfqs
Query visible RFQs
GET
/v1/rfqs/trades
Query anonymous RFQ-originated fills
POST
/v1/rfqs
Create an RFQ
DELETE
/v1/rfqs/{rfqId}
Close your open RFQ
GET
/v1/rfqs/quotes
Query visible quotes
POST
/v1/rfqs/quotes
Create or replace your quote
DELETE
/v1/rfqs/{rfqId}/quotes/{quoteId}
Delete your quote
PUT
/v1/rfqs/{rfqId}/quotes/{quoteId}/accept
Accept one side of a quote
PUT
/v1/rfqs/{rfqId}/quotes/{quoteId}/confirm
Confirm an accepted quote during last look
On the Retail API, Combo and RFQ creation share an additional
edge rate limit
of 10 requests per 10 seconds, enforced per API key and per IP. RFQ-specific business limits and participant restrictions are enforced separately by the RFQ service.
For
GET /v1/rfqs/quotes
, provide an
rfqId
or exactly one of
userFilter=USER_FILTER_SELF
and
rfqUserFilter=USER_FILTER_SELF
. Cursors are opaque and must be reused with the same filters and authenticated participant.
​
RFQ Trade History
GET /v1/rfqs/trades
returns anonymous fills where either order originated from an RFQ, including single instruments, combos, and later fills on resting orders. All participants see the same trades. Prints contain no participant, account, order, RFQ, or quote IDs.
Parameter
Description
limit
Page size, from 1 to 100. Omitted or
0
means 100.
cursor
Opaque continuation from the previous response. URL-encode it as a query value.
startTime
Inclusive RFC 3339 execution time. Defaults to the start of available feed coverage.
endTime
Exclusive RFC 3339 execution time. Defaults to the time the first request was received.
symbol
Exact, case-sensitive instrument symbol. Omit for all symbols.
For example,
GET /v1/rfqs/trades?limit=100&symbol=caoc-example
can return:
{
"trades"
: [
{
"tradeId"
:
"trade-example"
,
"symbol"
:
"caoc-example"
,
"price"
:
"0.1234"
,
"qtyDecimal"
:
"12.3456"
,
"aggressorSide"
:
"SIDE_BUY"
,
"executedTime"
:
"2026-10-01T12:34:56.123456789Z"
}
],
"cursor"
:
"opaque-continuation"
}
Prices and quantities are decimal strings.
aggressorSide
is the incoming order’s side (
SIDE_BUY
or
SIDE_SELL
). Results are ordered by execution time descending, then trade ID descending.
​
Pagination and Recovery
Repeat the same authenticated participant, filters, and limit on every continuation, changing only
cursor
. Keep omitted time bounds omitted; the cursor preserves them. Continue until the response cursor is empty, even if a page contains no trades.
On startup or reconnect, subscribe to the
RFQ WebSocket
first, then query overlapping history and deduplicate by
tradeId
. History is eventually visible and pagination is not a snapshot. Repeat overlapping queries to find late arrivals.
These are original prints: later corrections and busts do not amend them. Use your order and account data for reconciliation.
Invalid queries or cursors return HTTP
400
. Requests before available coverage also return
400
; unavailable history or a feed coverage gap returns
503
.
​
Replace a quote
Every successful
POST /v1/rfqs/quotes
returns a new
quoteId
, including replacements. Send the same
rfqId
with new prices. Use the returned ID to delete the new quote; use
quoteAccepted.quote.id
to confirm or decline an accepted quote.
quoteDeleted
identifies a canceled old quote;
quoteCreated
carries the new ID. Check
GET /v1/rfqs/quotes
if an older quote’s state is unclear.
​
RFQ price tick
tickSize
is the instrument’s minimum price increment in dollars. It appears on RFQs returned by
GET /v1/rfqs
and in
rfqCreated
and
rfqClosed
WebSocket events.
Quote prices must be multiples of
tickSize
and within the instrument’s price limits. For example,
"0.1234"
is aligned to a
0.0001
tick but not a
0.001
tick.
If
tickSize
is absent, read it from
GET /v1/combos?symbol=<rfq.symbol>
.
​
Real-time stream
RFQ and quote lifecycle events and anonymous
rfqTrade
prints are available on the
Private WebSocket
. Subscribe with
SUBSCRIPTION_TYPE_RFQ
.
For missed events, follow
Pagination and Recovery
. Reconcile RFQ and quote state with
GET /v1/rfqs
and
GET /v1/rfqs/quotes
.
​
Execution
QUOTE_STATUS_EXECUTED
and
quoteExecuted
mean the paired exchange orders were submitted and their order IDs were recorded. They do not mean the orders filled.
Use
SUBSCRIPTION_TYPE_RFQ
for the RFQ lifecycle and anonymous trade prints, and
SUBSCRIPTION_TYPE_ORDER
for your own fills, rejections, cancellations, and expirations. Correlate your orders using
creatorOrderId
for the maker and
rfqCreatorOrderId
for the requester; both IDs are also returned by
GET /v1/rfqs/quotes
. Anonymous prints cannot be linked to your order IDs.
RFQ orders enter the normal combo order book and may trade with other resting liquidity. Combo instruments can also be traded directly through the
Orders API
; using an RFQ is optional. If either
restRemainder
setting is true, unfilled quantity on that side may remain on the book.
​
See Also
Combos API
Create and read combo instruments
Private WebSocket
Receive RFQ lifecycle events and anonymous trade prints
Authentication
Sign Retail API requests
```

### RFQs Endpoints
**Source Routing Target:** https://docs.polymarket.us/api-reference/rfqs/endpoints

```text
ERROR: Status code 404
```

## Section: Portfolio
---

### Portfolio API Overview
**Source Routing Target:** https://docs.polymarket.us/api-reference/portfolio/overview

```text
​
Portfolio API
The Portfolio API provides access to user positions, account balances, and trading activity history.
Authentication Required
All Portfolio API endpoints require API key authentication. See the
Authentication guide
for details on signing requests.
​
Base URL
https://api.polymarket.us
​
Endpoints
​
Positions
Method
Endpoint
Description
GET
/v1/portfolio/positions
Get user’s trading positions
​
Activities
Method
Endpoint
Description
GET
/v1/portfolio/activities
Get trading activity history
​
Account
Method
Endpoint
Description
GET
/v1/account/balances
Get account balances
​
Positions Response
The positions response returns a
map of market slug to position
, not an array:
{
"positions"
: {
"will-x-happen"
: {
"netPosition"
:
"20"
,
"netPositionDecimal"
:
"19.6000"
,
"qtyBought"
:
"20"
,
"qtyBoughtDecimal"
:
"19.6000"
,
"qtySold"
:
"0"
,
"qtySoldDecimal"
:
"0.0000"
,
...
},
"another-market"
: {
"netPosition"
:
"-50"
,
...
}
},
"nextCursor"
:
"abc123"
,
"eof"
:
false
}
​
Position Fields
Field
Type
Description
netPositionDecimal
string (decimal)
Net position quantity in contracts (positive = long, negative = short)
qtyBoughtDecimal
string (decimal)
Total quantity bought in contracts
qtySoldDecimal
string (decimal)
Total quantity sold in contracts
qtyAvailableDecimal
string (decimal)
Quantity available to trade in contracts
bodPositionDecimal
string (decimal)
Beginning of day position in contracts
netPosition
string (int64)
Deprecated rounded quantity; use
netPositionDecimal
qtyBought
string (int64)
Deprecated rounded quantity; use
qtyBoughtDecimal
qtySold
string (int64)
Deprecated rounded quantity; use
qtySoldDecimal
cost
Amount
Total cost basis
realized
Amount
Realized profit/loss
cashValue
Amount
Current unrealized value
qtyAvailable
string (int64)
Deprecated rounded quantity; use
qtyAvailableDecimal
bodPosition
string (int64)
Deprecated rounded quantity; use
bodPositionDecimal
expired
boolean
Whether the position has expired
updateTime
string (date-time)
Last update timestamp
marketMetadata
object
Market information (slug, title, outcome)
Use the
*Decimal
quantity fields for display and calculations. The older integer fields remain for backward compatibility and should not be used for partial-contract markets.
​
Activities Response
Activities are returned as an array with pagination:
{
"activities"
: [
{
"type"
:
"ACTIVITY_TYPE_TRADE"
,
"trade"
: {
...
}
}
],
"nextCursor"
:
"xyz789"
,
"eof"
:
false
}
​
Activity Structure
Each activity has a
type
field and a corresponding nested object:
Type
Nested Field
Description
ACTIVITY_TYPE_TRADE
trade
Trade execution details
ACTIVITY_TYPE_POSITION_RESOLUTION
positionResolution
Market settlement details
ACTIVITY_TYPE_ACCOUNT_DEPOSIT
accountBalanceChange
Deposit details
ACTIVITY_TYPE_ACCOUNT_ADVANCED_DEPOSIT
accountBalanceChange
Advance issued against a pending deposit
ACTIVITY_TYPE_ACCOUNT_WITHDRAWAL
accountBalanceChange
Withdrawal details
ACTIVITY_TYPE_TRANSFER
accountBalanceChange
Transfer details
ACTIVITY_TYPE_REFERRAL_BONUS
accountBalanceChange
Referral incentive credit
ACTIVITY_TYPE_TAKER_FEE_REBATE
accountBalanceChange
Taker fee rebate credit
ACTIVITY_TYPE_LIQUIDITY_PROGRAM
accountBalanceChange
Liquidity program payout
​
Trade Object
Field
Type
Description
id
string
Exchange-assigned trade ID
marketSlug
string
Market slug
state
string
Trade state; see
Trade States
price
Amount
Trade price
qtyDecimal
string (decimal)
Trade quantity in contracts
qty
string
Deprecated rounded quantity; use
qtyDecimal
isAggressor
boolean
True if user’s order was the taker
costBasis
Amount
Cost basis for the trade
realizedPnl
Amount
Realized profit/loss
createTime
string (date-time)
Creation timestamp
updateTime
string (date-time)
Last update timestamp
​
Trade States
The
state
field on a trade progresses through the following values:
State
Value
Description
TRADE_STATE_NEW
1
Trade created.
TRADE_STATE_CLEARED
2
Trade successfully cleared by the clearing house.
TRADE_STATE_BUSTED
3
The trade was voided post-execution by the exchange (an error trade) and the resulting position was rolled back. This is a terminal reversal,
not
a pending state.
TRADE_STATE_INFLIGHT
4
Trade information sent to the clearinghouse.
TRADE_STATE_PENDING_RISK
5
Clearinghouse is pending at least one DCM claim for the trade.
TRADE_STATE_PENDING_CLEARED
6
Clearinghouse is pending the counterparty DCM claim.
TRADE_STATE_REJECTED
7
Clearinghouse rejected the trade.
TRADE_STATE_CLEARING_ACKNOWLEDGED
8
Clearing request acknowledged by the clearing house.
TRADE_STATE_RETRY_REQUEST
9
Retry requested; pending resubmission to the clearing house.
Handling
TRADE_STATE_BUSTED
A busted trade was executed and then voided by the exchange (via an error-trade
bust), and its position impact was reversed. Busted trades remain visible in trade
history — treat them as reversed for position, P&L, and reconciliation purposes.
Do not silently drop them.
TRADE_STATE_UNDEFINED
(value
0
) is the unset/unknown sentinel. It is omitted
from API responses and does not appear in the published enum lists. Treat any
unrecognized state value defensively rather than assuming the values above are
exhaustive.
​
Position Resolution Object
Field
Type
Description
marketSlug
string
Market slug
beforePosition
UserPosition
Position before resolution
afterPosition
UserPosition
Position after resolution
side
string
Resolution side (LONG, SHORT, NEUTRAL)
tradeId
string
Associated trade ID
updateTime
string (date-time)
Resolution timestamp
​
Account Balance Change Object
Field
Type
Description
transactionId
string
Transaction ID
status
string
Status (PENDING, COMPLETED, REJECTED)
amount
Amount
Amount of the balance change
createTime
string (date-time)
Creation timestamp
updateTime
string (date-time)
Last update timestamp
​
Pagination
Both endpoints support cursor-based pagination. Use
cursor
parameter with the
nextCursor
value to fetch the next page. When
eof
is
true
, there are no more results.
Real-Time Position Updates
For real-time position changes, use the
WebSocket Private Stream
with the
SUBSCRIPTION_TYPE_POSITION
subscription instead of polling.
​
Filtering Activities
Filter activities by type and market:
GET
/v1/portfolio/activities?types=ACTIVITY_TYPE_TRADE
&
marketSlug
=
will-x-happen
​
Sort Order
Activities can be sorted ascending or descending by time:
Sort Order
Description
SORT_ORDER_DESCENDING
Newest first (default)
SORT_ORDER_ASCENDING
Oldest first
​
Account Balances
The account balances endpoint returns current balance information:
{
"balances"
: [
{
"currentBalance"
:
1000.00
,
"currency"
:
"USD"
,
"buyingPower"
:
850.00
,
"assetNotional"
:
500.00
,
"assetAvailable"
:
250.00
,
"openOrders"
:
400.00
,
"unsettledFunds"
:
0
,
"marginRequirement"
:
0
,
"lastUpdated"
:
"2024-01-15T10:30:00Z"
}
]
}
​
Balance Fields
Field
Description
currentBalance
Current fiat currency balance
currency
Currency code (e.g., USD)
buyingPower
Capital available for trading
assetNotional
Total notional value of securities
assetAvailable
Available collateral value
pendingCredit
Pending credit amounts
openOrders
Value tied up in open orders
unsettledFunds
Unsettled funds not yet available
marginRequirement
Required margin for positions
​
Buying Power
The
buyingPower
field represents unencumbered capital available for trading:
buyingPower = currentBalance
+ assetAvailable
- openOrders
- marginRequirement
Real-Time Balance Updates
For real-time balance changes, use the
WebSocket Private Stream
with the
SUBSCRIPTION_TYPE_ACCOUNT_BALANCE
subscription instead of polling.
```

### Get User Positions (GET)
**Source Routing Target:** https://docs.polymarket.us/api-reference/portfolio/get-positions

```text
ERROR: Status code 404
```

### Get Activities (GET)
**Source Routing Target:** https://docs.polymarket.us/api-reference/portfolio/get-activities

```text
Get Activities
cURL
curl
--request
GET
\
--url
https://api.polymarket.us/v1/portfolio/activities
\
--header
'X-PM-Access-Key: <api-key>'
\
--header
'X-PM-Signature: <api-key>'
\
--header
'X-PM-Timestamp: <api-key>'
import requests
url = "https://api.polymarket.us/v1/portfolio/activities"
headers = {
"X-PM-Access-Key": "<api-key>",
"X-PM-Timestamp": "<api-key>",
"X-PM-Signature": "<api-key>"
}
response = requests.get(url, headers=headers)
print(response.text)
const options = {
method: 'GET',
headers: {
'X-PM-Access-Key': '<api-key>',
'X-PM-Timestamp': '<api-key>',
'X-PM-Signature': '<api-key>'
}
};
fetch('https://api.polymarket.us/v1/portfolio/activities', options)
.then(res => res.json())
.then(res => console.log(res))
.catch(err => console.error(err));
<?php
$curl = curl_init();
curl_setopt_array($curl, [
CURLOPT_URL => "https://api.polymarket.us/v1/portfolio/activities",
CURLOPT_RETURNTRANSFER => true,
CURLOPT_ENCODING => "",
CURLOPT_MAXREDIRS => 10,
CURLOPT_TIMEOUT => 30,
CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
CURLOPT_CUSTOMREQUEST => "GET",
CURLOPT_HTTPHEADER => [
"X-PM-Access-Key: <api-key>",
"X-PM-Signature: <api-key>",
"X-PM-Timestamp: <api-key>"
],
]);
$response = curl_exec($curl);
$err = curl_error($curl);
curl_close($curl);
if ($err) {
echo "cURL Error #:" . $err;
} else {
echo $response;
}
package main
import (
"fmt"
"net/http"
"io"
)
func main() {
url := "https://api.polymarket.us/v1/portfolio/activities"
req, _ := http.NewRequest("GET", url, nil)
req.Header.Add("X-PM-Access-Key", "<api-key>")
req.Header.Add("X-PM-Timestamp", "<api-key>")
req.Header.Add("X-PM-Signature", "<api-key>")
res, _ := http.DefaultClient.Do(req)
defer res.Body.Close()
body, _ := io.ReadAll(res.Body)
fmt.Println(string(body))
}
HttpResponse<String> response = Unirest.get("https://api.polymarket.us/v1/portfolio/activities")
.header("X-PM-Access-Key", "<api-key>")
.header("X-PM-Timestamp", "<api-key>")
.header("X-PM-Signature", "<api-key>")
.asString();
require 'uri'
require 'net/http'
url = URI("https://api.polymarket.us/v1/portfolio/activities")
http = Net::HTTP.new(url.host, url.port)
http.use_ssl = true
request = Net::HTTP::Get.new(url)
request["X-PM-Access-Key"] = '<api-key>'
request["X-PM-Timestamp"] = '<api-key>'
request["X-PM-Signature"] = '<api-key>'
response = http.request(request)
puts response.read_body
200
{
"activities"
: [
{
"type"
:
"ACTIVITY_TYPE_TRADE"
,
"trade"
: {
"id"
:
"<string>"
,
"marketSlug"
:
"<string>"
,
"state"
:
"TRADE_STATE_NEW"
,
"createTime"
:
"2023-11-07T05:31:56Z"
,
"updateTime"
:
"2023-11-07T05:31:56Z"
,
"price"
: {
"value"
:
"123.45"
,
"currency"
:
"<string>"
},
"qty"
:
"<string>"
,
"isAggressor"
:
true
,
"costBasis"
: {
"value"
:
"123.45"
,
"currency"
:
"<string>"
},
"realizedPnl"
: {
"value"
:
"123.45"
,
"currency"
:
"<string>"
},
"qtyDecimal"
:
"<string>"
},
"positionResolution"
: {
"marketSlug"
:
"<string>"
,
"beforePosition"
: {
"netPosition"
:
"<string>"
,
"qtyBought"
:
"<string>"
,
"qtySold"
:
"<string>"
,
"cost"
: {
"value"
:
"123.45"
,
"currency"
:
"<string>"
},
"realized"
: {
"value"
:
"123.45"
,
"currency"
:
"<string>"
},
"bodPosition"
:
"<string>"
,
"expired"
:
true
,
"updateTime"
:
"2023-11-07T05:31:56Z"
,
"marketMetadata"
: {
"slug"
:
"<string>"
,
"icon"
:
"<string>"
,
"title"
:
"<string>"
,
"outcome"
:
"<string>"
,
"eventSlug"
:
"<string>"
},
"cashValue"
: {
"value"
:
"123.45"
,
"currency"
:
"<string>"
},
"qtyAvailable"
:
"<string>"
,
"netPositionDecimal"
:
"<string>"
,
"qtyBoughtDecimal"
:
"<string>"
,
"qtySoldDecimal"
:
"<string>"
,
"bodPositionDecimal"
:
"<string>"
,
"qtyAvailableDecimal"
:
"<string>"
},
"afterPosition"
: {
"netPosition"
:
"<string>"
,
"qtyBought"
:
"<string>"
,
"qtySold"
:
"<string>"
,
"cost"
: {
"value"
:
"123.45"
,
"currency"
:
"<string>"
},
"realized"
: {
"value"
:
"123.45"
,
"currency"
:
"<string>"
},
"bodPosition"
:
"<string>"
,
"expired"
:
true
,
"updateTime"
:
"2023-11-07T05:31:56Z"
,
"marketMetadata"
: {
"slug"
:
"<string>"
,
"icon"
:
"<string>"
,
"title"
:
"<string>"
,
"outcome"
:
"<string>"
,
"eventSlug"
:
"<string>"
},
"cashValue"
: {
"value"
:
"123.45"
,
"currency"
:
"<string>"
},
"qtyAvailable"
:
"<string>"
,
"netPositionDecimal"
:
"<string>"
,
"qtyBoughtDecimal"
:
"<string>"
,
"qtySoldDecimal"
:
"<string>"
,
"bodPositionDecimal"
:
"<string>"
,
"qtyAvailableDecimal"
:
"<string>"
},
"updateTime"
:
"2023-11-07T05:31:56Z"
,
"tradeId"
:
"<string>"
,
"side"
:
"POSITION_RESOLUTION_SIDE_LONG"
},
"accountBalanceChange"
: {
"transactionId"
:
"<string>"
,
"status"
:
"ACCOUNT_BALANCE_CHANGE_STATUS_PENDING"
,
"amount"
: {
"value"
:
"123.45"
,
"currency"
:
"<string>"
},
"updateTime"
:
"2023-11-07T05:31:56Z"
,
"createTime"
:
"2023-11-07T05:31:56Z"
}
}
],
"nextCursor"
:
"<string>"
,
"eof"
:
true
}
GET
/
v1
/
portfolio
/
activities
Try it
Get Activities
cURL
curl
--request
GET
\
--url
https://api.polymarket.us/v1/portfolio/activities
\
--header
'X-PM-Access-Key: <api-key>'
\
--header
'X-PM-Signature: <api-key>'
\
--header
'X-PM-Timestamp: <api-key>'
import requests
url = "https://api.polymarket.us/v1/portfolio/activities"
headers = {
"X-PM-Access-Key": "<api-key>",
"X-PM-Timestamp": "<api-key>",
"X-PM-Signature": "<api-key>"
}
response = requests.get(url, headers=headers)
print(response.text)
const options = {
method: 'GET',
headers: {
'X-PM-Access-Key': '<api-key>',
'X-PM-Timestamp': '<api-key>',
'X-PM-Signature': '<api-key>'
}
};
fetch('https://api.polymarket.us/v1/portfolio/activities', options)
.then(res => res.json())
.then(res => console.log(res))
.catch(err => console.error(err));
<?php
$curl = curl_init();
curl_setopt_array($curl, [
CURLOPT_URL => "https://api.polymarket.us/v1/portfolio/activities",
CURLOPT_RETURNTRANSFER => true,
CURLOPT_ENCODING => "",
CURLOPT_MAXREDIRS => 10,
CURLOPT_TIMEOUT => 30,
CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
CURLOPT_CUSTOMREQUEST => "GET",
CURLOPT_HTTPHEADER => [
"X-PM-Access-Key: <api-key>",
"X-PM-Signature: <api-key>",
"X-PM-Timestamp: <api-key>"
],
]);
$response = curl_exec($curl);
$err = curl_error($curl);
curl_close($curl);
if ($err) {
echo "cURL Error #:" . $err;
} else {
echo $response;
}
package main
import (
"fmt"
"net/http"
"io"
)
func main() {
url := "https://api.polymarket.us/v1/portfolio/activities"
req, _ := http.NewRequest("GET", url, nil)
req.Header.Add("X-PM-Access-Key", "<api-key>")
req.Header.Add("X-PM-Timestamp", "<api-key>")
req.Header.Add("X-PM-Signature", "<api-key>")
res, _ := http.DefaultClient.Do(req)
defer res.Body.Close()
body, _ := io.ReadAll(res.Body)
fmt.Println(string(body))
}
HttpResponse<String> response = Unirest.get("https://api.polymarket.us/v1/portfolio/activities")
.header("X-PM-Access-Key", "<api-key>")
.header("X-PM-Timestamp", "<api-key>")
.header("X-PM-Signature", "<api-key>")
.asString();
require 'uri'
require 'net/http'
url = URI("https://api.polymarket.us/v1/portfolio/activities")
http = Net::HTTP.new(url.host, url.port)
http.use_ssl = true
request = Net::HTTP::Get.new(url)
request["X-PM-Access-Key"] = '<api-key>'
request["X-PM-Timestamp"] = '<api-key>'
request["X-PM-Signature"] = '<api-key>'
response = http.request(request)
puts response.read_body
200
{
"activities"
: [
{
"type"
:
"ACTIVITY_TYPE_TRADE"
,
"trade"
: {
"id"
:
"<string>"
,
"marketSlug"
:
"<string>"
,
"state"
:
"TRADE_STATE_NEW"
,
"createTime"
:
"2023-11-07T05:31:56Z"
,
"updateTime"
:
"2023-11-07T05:31:56Z"
,
"price"
: {
"value"
:
"123.45"
,
"currency"
:
"<string>"
},
"qty"
:
"<string>"
,
"isAggressor"
:
true
,
"costBasis"
: {
"value"
:
"123.45"
,
"currency"
:
"<string>"
},
"realizedPnl"
: {
"value"
:
"123.45"
,
"currency"
:
"<string>"
},
"qtyDecimal"
:
"<string>"
},
"positionResolution"
: {
"marketSlug"
:
"<string>"
,
"beforePosition"
: {
"netPosition"
:
"<string>"
,
"qtyBought"
:
"<string>"
,
"qtySold"
:
"<string>"
,
"cost"
: {
"value"
:
"123.45"
,
"currency"
:
"<string>"
},
"realized"
: {
"value"
:
"123.45"
,
"currency"
:
"<string>"
},
"bodPosition"
:
"<string>"
,
"expired"
:
true
,
"updateTime"
:
"2023-11-07T05:31:56Z"
,
"marketMetadata"
: {
"slug"
:
"<string>"
,
"icon"
:
"<string>"
,
"title"
:
"<string>"
,
"outcome"
:
"<string>"
,
"eventSlug"
:
"<string>"
},
"cashValue"
: {
"value"
:
"123.45"
,
"currency"
:
"<string>"
},
"qtyAvailable"
:
"<string>"
,
"netPositionDecimal"
:
"<string>"
,
"qtyBoughtDecimal"
:
"<string>"
,
"qtySoldDecimal"
:
"<string>"
,
"bodPositionDecimal"
:
"<string>"
,
"qtyAvailableDecimal"
:
"<string>"
},
"afterPosition"
: {
"netPosition"
:
"<string>"
,
"qtyBought"
:
"<string>"
,
"qtySold"
:
"<string>"
,
"cost"
: {
"value"
:
"123.45"
,
"currency"
:
"<string>"
},
"realized"
: {
"value"
:
"123.45"
,
"currency"
:
"<string>"
},
"bodPosition"
:
"<string>"
,
"expired"
:
true
,
"updateTime"
:
"2023-11-07T05:31:56Z"
,
"marketMetadata"
: {
"slug"
:
"<string>"
,
"icon"
:
"<string>"
,
"title"
:
"<string>"
,
"outcome"
:
"<string>"
,
"eventSlug"
:
"<string>"
},
"cashValue"
: {
"value"
:
"123.45"
,
"currency"
:
"<string>"
},
"qtyAvailable"
:
"<string>"
,
"netPositionDecimal"
:
"<string>"
,
"qtyBoughtDecimal"
:
"<string>"
,
"qtySoldDecimal"
:
"<string>"
,
"bodPositionDecimal"
:
"<string>"
,
"qtyAvailableDecimal"
:
"<string>"
},
"updateTime"
:
"2023-11-07T05:31:56Z"
,
"tradeId"
:
"<string>"
,
"side"
:
"POSITION_RESOLUTION_SIDE_LONG"
},
"accountBalanceChange"
: {
"transactionId"
:
"<string>"
,
"status"
:
"ACCOUNT_BALANCE_CHANGE_STATUS_PENDING"
,
"amount"
: {
"value"
:
"123.45"
,
"currency"
:
"<string>"
},
"updateTime"
:
"2023-11-07T05:31:56Z"
,
"createTime"
:
"2023-11-07T05:31:56Z"
}
}
],
"nextCursor"
:
"<string>"
,
"eof"
:
true
}
Authorizations
​
X-PM-Access-Key
string
header
required
Your API key ID (UUID). Generate at
polymarket.us/developer
.
​
X-PM-Timestamp
string
header
required
Unix timestamp in milliseconds. Must be within 30 seconds of server time.
​
X-PM-Signature
string
header
required
Base64-encoded Ed25519 signature of
timestamp + method + path
. See
Authentication
for details.
Query Parameters
​
limit
integer<int32>
Maximum number of activities to return per page. Use with
cursor
for pagination. Default:
100
. Example:
50
​
cursor
string
Pagination cursor from a previous response's
nextCursor
field. Use to fetch the next page of results. Omit for the first request
​
marketSlug
string
Filter activities by a specific market slug. Returns only activities (trades, resolutions) related to that market. Example:
will-team-a-win
​
types
enum<string>[]
Filter by activity types. When specified, only returns activities of the selected types. TRADE (order executions), POSITION_RESOLUTION (market settlements), ACCOUNT_DEPOSIT/WITHDRAWAL (fund transfers)
Available options
:
ACTIVITY_TYPE_TRADE
,
ACTIVITY_TYPE_POSITION_RESOLUTION
,
ACTIVITY_TYPE_ACCOUNT_DEPOSIT
,
ACTIVITY_TYPE_ACCOUNT_ADVANCED_DEPOSIT
,
ACTIVITY_TYPE_ACCOUNT_WITHDRAWAL
,
ACTIVITY_TYPE_REFERRAL_BONUS
,
ACTIVITY_TYPE_TRANSFER
,
ACTIVITY_TYPE_TAKER_FEE_REBATE
,
ACTIVITY_TYPE_LIQUIDITY_PROGRAM
​
sortOrder
enum<string>
Sort order for activities by timestamp. DESCENDING returns newest first (default), ASCENDING returns oldest first
Available options
:
SORT_ORDER_DESCENDING
,
SORT_ORDER_ASCENDING
Response
200
application/json
List of activities
​
activities
object[]
List of activities
Show
child attributes
​
nextCursor
string
Pagination cursor for next page
​
eof
boolean
True if this is the last page
```

### Get Account Balances (GET)
**Source Routing Target:** https://docs.polymarket.us/api-reference/portfolio/get-balances

```text
ERROR: Status code 404
```

## Section: Events
---

### Events API Overview
**Source Routing Target:** https://docs.polymarket.us/api-reference/events/overview

```text
​
Events API
The Events API provides access to event information. For search, see the Search API.
​
Endpoints
Method
Endpoint
Description
GET
/v1/events
Get all events with filtering
GET
/v1/events/{id}
Get event by ID
GET
/v1/events/slug/{slug}
Get event by slug
GET
/v1/partners/{partnerKey}/events/{externalId}
Get partner event by external ID
​
Key Event Fields
Field
Description
id
Unique event identifier
slug
URL-friendly identifier
title
Event title
description
Event description
category
Event category
subcategory
Event subcategory
active
Whether event is active
closed
Whether event is closed
archived
Whether event is archived
​
Sports Event Fields
Field
Description
gameId
Sports provider game ID
sportradarGameId
Sportradar game ID
score
Current event score
period
Current period
live
Whether event is live
ended
Whether event has ended
eventState
Detailed event state information
participants
Event participants (teams/players)
​
Crypto Event Fields
Crypto price events have no participants or game state. Use these fields instead:
Field
Description
seriesSlug
Asset, family and cadence, e.g.
btc-updown-15m
,
btc-strike-daily
,
btc-range-hourly
,
btc-hit-monthly
tags
Taxonomy tags such as
crypto
,
crypto-prices
,
recurring
, the family (
up-or-down
,
multi-strikes
,
neg-risk
,
hit-price
), the window (
15M
,
1H
,
daily
,
weekly
,
monthly
) and the asset (
bitcoin
)
markets[].assetPriceTerms
Typed terms of each leg; see
Crypto Price Market Fields
An Up/Down event holds one market per window; a ladder event holds one market per strike or bucket.
​
Volume & Liquidity
Field
Description
liquidity
Event liquidity
volume
Total trading volume
volume24hr
24-hour volume
volume1wk
7-day volume
volume1mo
30-day volume
​
Filtering Events
Query events with various filters:
GET
/v1/events?active=
true
&
categories
=
sports
&
limit
=
50
​
Common Filters
Parameter
Type
Description
active
boolean
Filter by active status
closed
boolean
Filter by closed status
archived
boolean
Filter by archived status
featured
boolean
Filter featured events
categories
array
Filter by categories
seriesId
array
Filter by series IDs
gameId
integer
Filter by game ID
ended
boolean
Filter by ended status
live
boolean
Filter live events
​
Date Filters
Parameter
Type
Description
startDateMin
string
Minimum start date
startDateMax
string
Maximum start date
startTimeMin
string
Minimum start time
startTimeMax
string
Maximum start time
eventDate
string
Specific event date
eventWeek
integer
Event week number
​
Partner Events
Retrieve an event using a partner’s external ID:
GET
/v1/partners/{partnerKey}/events/{externalId}
​
Path Parameters
Parameter
Type
Description
partnerKey
string
Partner key identifier
externalId
string
Partner’s external event ID
```

### Get Event By ID (GET)
**Source Routing Target:** https://docs.polymarket.us/api-reference/events/get-by-id

```text
ERROR: Status code 404
```

### Get Event By Slug (GET)
**Source Routing Target:** https://docs.polymarket.us/api-reference/events/get-by-slug

```text
ERROR: Status code 404
```

### Get Event By Partner External ID (GET)
**Source Routing Target:** https://docs.polymarket.us/api-reference/events/get-by-partner

```text
ERROR: Status code 404
```

### Get Events (GET)
**Source Routing Target:** https://docs.polymarket.us/api-reference/events/get-events

```text
Get Events
cURL
curl
--request
GET
\
--url
https://gateway.polymarket.us/v1/events
import requests
url = "https://gateway.polymarket.us/v1/events"
response = requests.get(url)
print(response.text)
const options = {method: 'GET'};
fetch('https://gateway.polymarket.us/v1/events', options)
.then(res => res.json())
.then(res => console.log(res))
.catch(err => console.error(err));
<?php
$curl = curl_init();
curl_setopt_array($curl, [
CURLOPT_URL => "https://gateway.polymarket.us/v1/events",
CURLOPT_RETURNTRANSFER => true,
CURLOPT_ENCODING => "",
CURLOPT_MAXREDIRS => 10,
CURLOPT_TIMEOUT => 30,
CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
CURLOPT_CUSTOMREQUEST => "GET",
]);
$response = curl_exec($curl);
$err = curl_error($curl);
curl_close($curl);
if ($err) {
echo "cURL Error #:" . $err;
} else {
echo $response;
}
package main
import (
"fmt"
"net/http"
"io"
)
func main() {
url := "https://gateway.polymarket.us/v1/events"
req, _ := http.NewRequest("GET", url, nil)
res, _ := http.DefaultClient.Do(req)
defer res.Body.Close()
body, _ := io.ReadAll(res.Body)
fmt.Println(string(body))
}
HttpResponse<String> response = Unirest.get("https://gateway.polymarket.us/v1/events")
.asString();
require 'uri'
require 'net/http'
url = URI("https://gateway.polymarket.us/v1/events")
http = Net::HTTP.new(url.host, url.port)
http.use_ssl = true
request = Net::HTTP::Get.new(url)
response = http.request(request)
puts response.read_body
200
{
"events"
: [
{
"id"
:
"<string>"
,
"ticker"
:
"<string>"
,
"slug"
:
"<string>"
,
"title"
:
"<string>"
,
"subtitle"
:
"<string>"
,
"description"
:
"<string>"
,
"resolutionSource"
:
"<string>"
,
"startDate"
:
"<string>"
,
"creationDate"
:
"<string>"
,
"endDate"
:
"<string>"
,
"image"
:
"<string>"
,
"imageDisplayType"
:
"IMAGE_DISPLAY_TYPE_HEADSHOT"
,
"active"
:
true
,
"closed"
:
true
,
"archived"
:
true
,
"liquidity"
:
123
,
"volume"
:
123
,
"openInterest"
:
123
,
"category"
:
"<string>"
,
"subcategory"
:
"<string>"
,
"createdAt"
:
"<string>"
,
"updatedAt"
:
"<string>"
,
"volume24hr"
:
123
,
"volume1wk"
:
123
,
"volume1mo"
:
123
,
"volume1yr"
:
123
,
"closedTime"
:
"<string>"
,
"eventDate"
:
"<string>"
,
"startTime"
:
"<string>"
,
"seriesSlug"
:
"<string>"
,
"score"
:
"<string>"
,
"elapsed"
:
"<string>"
,
"period"
:
"<string>"
,
"live"
:
true
,
"ended"
:
true
,
"finishedTimestamp"
:
"<string>"
,
"featuredOrder"
:
123
,
"markets"
: [
{
"id"
:
"<string>"
,
"question"
:
"<string>"
,
"slug"
:
"<string>"
,
"endDate"
:
"<string>"
,
"category"
:
"<string>"
,
"startDate"
:
"<string>"
,
"image"
:
"<string>"
,
"imageDisplayType"
:
"IMAGE_DISPLAY_TYPE_HEADSHOT"
,
"description"
:
"<string>"
,
"active"
:
true
,
"marketType"
:
"<string>"
,
"closed"
:
true
,
"createdAt"
:
"<string>"
,
"updatedAt"
:
"<string>"
,
"archived"
:
true
,
"orderPriceMinTickSize"
:
123
,
"gameStartTime"
:
"<string>"
,
"manualActivation"
:
true
,
"sportsMarketType"
:
"<string>"
,
"line"
:
123
,
"marketSides"
: [
{
"id"
:
"<string>"
,
"marketSideType"
:
"MARKET_SIDE_TYPE_ERC1155"
,
"identifier"
:
"<string>"
,
"createdAt"
:
"<string>"
,
"updatedAt"
:
"<string>"
,
"description"
:
"<string>"
,
"price"
:
"<string>"
,
"marketId"
:
123
,
"long"
:
true
,
"teamId"
:
123
,
"team"
: {
"id"
:
123
,
"name"
:
"<string>"
,
"abbreviation"
:
"<string>"
,
"league"
:
"<string>"
,
"record"
:
"<string>"
,
"logo"
:
"<string>"
,
"alias"
:
"<string>"
,
"safeName"
:
"<string>"
,
"homeIcon"
:
"<string>"
,
"awayIcon"
:
"<string>"
,
"colorPrimary"
:
"<string>"
,
"providerId"
:
123
,
"ordering"
:
"<string>"
,
"longIcon"
:
"<string>"
,
"shortIcon"
:
"<string>"
,
"displayAbbreviation"
:
"<string>"
,
"ranking"
:
"<string>"
,
"conference"
:
"<string>"
,
"providerIds"
: [
{
"provider"
:
"PROVIDER_SPORTSDATAIO"
,
"providerId"
:
"<string>"
}
],
"longIconDark"
:
"<string>"
,
"shortIconDark"
:
"<string>"
,
"color"
: {
"light"
:
"<string>"
,
"dark"
:
"<string>"
},
"imageDisplayType"
:
"IMAGE_DISPLAY_TYPE_HEADSHOT"
},
"quote"
: {
"value"
:
123.45
,
"currency"
:
"<string>"
},
"tradable"
:
true
}
],
"outcomes"
:
"<string>"
,
"outcomePrices"
:
"<string>"
,
"ep3Status"
:
"<string>"
,
"status"
:
"MARKET_STATUS_UNSPECIFIED"
,
"assetPriceTerms"
: {
"marketType"
:
"ASSET_PRICE_MARKET_TYPE_UNSPECIFIED"
,
"asset"
: {
"assetClass"
:
"ASSET_CLASS_CRYPTO"
,
"symbol"
:
"btc"
},
"indexSymbol"
:
"<string>"
,
"horizon"
:
"<string>"
,
"windowStart"
:
"2023-11-07T05:31:56Z"
,
"windowEnd"
:
"2023-11-07T05:31:56Z"
,
"priceToBeat"
: {
"value"
:
123.45
,
"currency"
:
"<string>"
},
"strike"
: {
"value"
:
123.45
,
"currency"
:
"<string>"
},
"rangeLower"
: {
"value"
:
123.45
,
"currency"
:
"<string>"
},
"rangeUpper"
: {
"value"
:
123.45
,
"currency"
:
"<string>"
},
"rangeKind"
:
"ASSET_PRICE_RANGE_KIND_UNSPECIFIED"
,
"direction"
:
"ASSET_PRICE_DIRECTION_UNSPECIFIED"
,
"settlementPrice"
: {
"value"
:
123.45
,
"currency"
:
"<string>"
}
},
"sportsMarketTypeV2"
:
"SPORTS_MARKET_TYPE_MONEYLINE"
,
"hidden"
:
true
,
"tags"
: [
{
"id"
:
"<string>"
,
"label"
:
"<string>"
,
"slug"
:
"<string>"
,
"createdAt"
:
"<string>"
,
"updatedAt"
:
"<string>"
,
"image"
:
"<string>"
,
"tradable"
:
true
,
"league"
: {
"id"
:
123
,
"name"
:
"<string>"
,
"sportId"
:
123
,
"tagId"
:
123
,
"image"
:
"<string>"
,
"resolution"
:
"<string>"
,
"ordering"
:
"<string>"
,
"activeSeriesId"
:
123
,
"isOperational"
:
true
,
"automaticResolution"
:
true
,
"createdAt"
:
"<string>"
,
"slug"
:
"<string>"
,
"abbreviation"
:
"<string>"
},
"sport"
: {
"id"
:
123
,
"name"
:
"<string>"
,
"tagId"
:
123
,
"createdAt"
:
"<string>"
,
"slug"
:
"<string>"
,
"image"
:
"<string>"
},
"parentId"
:
123
,
"subtags"
: [
{}
],
"hub"
: {
"id"
:
"<string>"
,
"title"
:
"<string>"
,
"image"
:
"<string>"
,
"subtitle"
:
"<string>"
,
"icon"
:
"<string>"
,
"status"
:
"HUB_STATUS_ACTIVE"
,
"startTime"
:
"2023-11-07T05:31:56Z"
}
}
],
"title"
:
"<string>"
,
"subtitle"
:
"<string>"
,
"color"
:
"<string>"
,
"darkColor"
:
"<string>"
,
"subjectId"
:
123
,
"subject"
: {
"id"
:
123
,
"name"
:
"<string>"
,
"displayName"
:
"<string>"
,
"description"
:
"<string>"
,
"subjectType"
:
"<string>"
,
"image"
:
"<string>"
,
"color"
:
"<string>"
,
"darkColor"
:
"<string>"
,
"createdAt"
:
"<string>"
,
"updatedAt"
:
"<string>"
,
"slug"
:
"<string>"
},
"feeCoefficient"
:
123
,
"spreadTotalSuffix"
:
"<string>"
,
"sortOrder"
:
123
,
"bestBidQuote"
: {
"value"
:
123.45
,
"currency"
:
"<string>"
},
"bestAskQuote"
: {
"value"
:
123.45
,
"currency"
:
"<string>"
},
"metadata"
: {},
"titleShort"
:
"<string>"
,
"ep3SyncedAt"
:
"<string>"
,
"minimumTradeQty"
:
123
,
"volume"
:
123
,
"volume24hr"
:
123
,
"volume1wk"
:
123
,
"volume1mo"
:
123
,
"volume1yr"
:
123
,
"rulesDisclaimer"
:
"<string>"
,
"rulesDisclaimerPopup"
:
true
,
"comboEnabled"
:
true
}
],
"gameId"
:
123
,
"rescheduledFromGameId"
:
123
,
"sportradarGameId"
:
"<string>"
,
"eventState"
: {
"id"
:
123
,
"gameId"
:
123
,
"sportradarGameId"
:
"<string>"
,
"type"
:
"<string>"
,
"createdAt"
:
"2023-11-07T05:31:56Z"
,
"updatedAt"
:
"2023-11-07T05:31:56Z"
,
"score"
:
"<string>"
,
"elapsed"
:
"<string>"
,
"period"
:
"<string>"
,
"live"
:
true
,
"ended"
:
true
,
"finishedTimestamp"
:
"2023-11-07T05:31:56Z"
,
"footballState"
: {
"down"
:
123
,
"yard"
:
123
,
"possessionProviderId"
:
"<string>"
,
"driveState"
: {
"down"
:
123
,
"yfd"
:
123
,
"possessionTeamId"
:
"<string>"
,
"fieldPosition"
: {
"teamId"
:
"<string>"
,
"yard"
:
123
},
"startFieldPosition"
: {
"teamId"
:
"<string>"
,
"yard"
:
123
}
},
"timeouts"
: [
{
"teamId"
:
"<string>"
,
"used"
:
123
,
"remaining"
:
123
}
]
},
"ufcState"
: {
"weightClass"
:
"<string>"
,
"cardSegment"
:
"<string>"
,
"eventLogo"
:
"<string>"
,
"rounds"
:
123
,
"order"
:
123
},
"tennisState"
: {
"tournamentName"
:
"<string>"
,
"round"
:
"<string>"
,
"servingTeamId"
:
123
},
"baseballState"
: {
"balls"
:
123
,
"strikes"
:
123
,
"outs"
:
123
,
"onFirst"
:
true
,
"onSecond"
:
true
,
"onThird"
:
true
,
"inningHalf"
:
"<string>"
},
"cricketState"
: {
"innings"
: [
{
"number"
:
123
,
"battingTeamId"
:
"<string>"
,
"runs"
:
123
,
"wickets"
:
123
,
"oversCompleted"
:
123
,
"complete"
:
true
,
"ballsIntoOver"
:
123
}
],
"currentInnings"
:
123
,
"totalOvers"
:
123
,
"phase"
:
"<string>"
,
"chase"
: {
"target"
:
123
,
"runsNeeded"
:
123
,
"ballsRemaining"
:
123
,
"currentRunRate"
:
123
,
"requiredRunRate"
:
123
}
},
"soccerState"
: {
"shootoutAttempts"
: [
{
"competitorId"
:
"<string>"
,
"status"
:
"SOCCER_PENALTY_SHOOTOUT_ATTEMPT_STATUS_NOT_TAKEN_YET"
,
"playerId"
:
"<string>"
,
"playerName"
:
"<string>"
}
]
},
"mainSpreadLine"
:
123
,
"mainTotalLine"
:
123
,
"marketGroupStats"
: [
{
"marketGroupId"
:
"<string>"
,
"line"
:
123
,
"current"
:
123
}
],
"periodScores"
: [
{
"number"
:
123
,
"type"
:
"PERIOD_SCORE_TYPE_REGULATION"
,
"label"
:
"<string>"
,
"scores"
: [
{
"competitorId"
:
"<string>"
,
"score"
:
123
}
]
}
],
"eventId"
:
123
},
"hidden"
:
true
,
"tags"
: [
{
"id"
:
"<string>"
,
"label"
:
"<string>"
,
"slug"
:
"<string>"
,
"createdAt"
:
"<string>"
,
"updatedAt"
:
"<string>"
,
"image"
:
"<string>"
,
"tradable"
:
true
,
"league"
: {
"id"
:
123
,
"name"
:
"<string>"
,
"sportId"
:
123
,
"tagId"
:
123
,
"image"
:
"<string>"
,
"resolution"
:
"<string>"
,
"ordering"
:
"<string>"
,
"activeSeriesId"
:
123
,
"isOperational"
:
true
,
"automaticResolution"
:
true
,
"createdAt"
:
"<string>"
,
"slug"
:
"<string>"
,
"abbreviation"
:
"<string>"
},
"sport"
: {
"id"
:
123
,
"name"
:
"<string>"
,
"tagId"
:
123
,
"createdAt"
:
"<string>"
,
"slug"
:
"<string>"
,
"image"
:
"<string>"
},
"parentId"
:
123
,
"subtags"
: [
{}
],
"hub"
: {
"id"
:
"<string>"
,
"title"
:
"<string>"
,
"image"
:
"<string>"
,
"subtitle"
:
"<string>"
,
"icon"
:
"<string>"
,
"status"
:
"HUB_STATUS_ACTIVE"
,
"startTime"
:
"2023-11-07T05:31:56Z"
}
}
],
"teams"
: [
{
"id"
:
123
,
"name"
:
"<string>"
,
"abbreviation"
:
"<string>"
,
"league"
:
"<string>"
,
"record"
:
"<string>"
,
"logo"
:
"<string>"
,
"alias"
:
"<string>"
,
"safeName"
:
"<string>"
,
"homeIcon"
:
"<string>"
,
"awayIcon"
:
"<string>"
,
"colorPrimary"
:
"<string>"
,
"providerId"
:
123
,
"ordering"
:
"<string>"
,
"longIcon"
:
"<string>"
,
"shortIcon"
:
"<string>"
,
"displayAbbreviation"
:
"<string>"
,
"ranking"
:
"<string>"
,
"conference"
:
"<string>"
,
"providerIds"
: [
{
"provider"
:
"PROVIDER_SPORTSDATAIO"
,
"providerId"
:
"<string>"
}
],
"longIconDark"
:
"<string>"
,
"shortIconDark"
:
"<string>"
,
"color"
: {
"light"
:
"<string>"
,
"dark"
:
"<string>"
},
"imageDisplayType"
:
"IMAGE_DISPLAY_TYPE_HEADSHOT"
}
],
"metadata"
: {
"gameState"
: {
"id"
:
123
,
"gameId"
:
123
,
"sportradarGameId"
:
"<string>"
,
"type"
:
"<string>"
,
"createdAt"
:
"2023-11-07T05:31:56Z"
,
"updatedAt"
:
"2023-11-07T05:31:56Z"
,
"score"
:
"<string>"
,
"elapsed"
:
"<string>"
,
"period"
:
"<string>"
,
"live"
:
true
,
"ended"
:
true
,
"finishedTimestamp"
:
"2023-11-07T05:31:56Z"
,
"footballState"
: {
"down"
:
123
,
"yard"
:
123
,
"possessionProviderId"
:
"<string>"
,
"driveState"
: {
"down"
:
123
,
"yfd"
:
123
,
"possessionTeamId"
:
"<string>"
,
"fieldPosition"
: {
"teamId"
:
"<string>"
,
"yard"
:
123
},
"startFieldPosition"
: {
"teamId"
:
"<string>"
,
"yard"
:
123
}
},
"timeouts"
: [
{
"teamId"
:
"<string>"
,
"used"
:
123
,
"remaining"
:
123
}
]
},
"ufcState"
: {
"weightClass"
:
"<string>"
,
"cardSegment"
:
"<string>"
,
"eventLogo"
:
"<string>"
,
"rounds"
:
123
,
"order"
:
123
},
"tennisState"
: {
"tournamentName"
:
"<string>"
,
"round"
:
"<string>"
,
"servingTeamId"
:
123
},
"baseballState"
: {
"balls"
:
123
,
"strikes"
:
123
,
"outs"
:
123
,
"onFirst"
:
true
,
"onSecond"
:
true
,
"onThird"
:
true
,
"inningHalf"
:
"<string>"
},
"cricketState"
: {
"innings"
: [
{
"number"
:
123
,
"battingTeamId"
:
"<string>"
,
"runs"
:
123
,
"wickets"
:
123
,
"oversCompleted"
:
123
,
"complete"
:
true
,
"ballsIntoOver"
:
123
}
],
"currentInnings"
:
123
,
"totalOvers"
:
123
,
"phase"
:
"<string>"
,
"chase"
: {
"target"
:
123
,
"runsNeeded"
:
123
,
"ballsRemaining"
:
123
,
"currentRunRate"
:
123
,
"requiredRunRate"
:
123
}
},
"soccerState"
: {
"shootoutAttempts"
: [
{
"competitorId"
:
"<string>"
,
"status"
:
"SOCCER_PENALTY_SHOOTOUT_ATTEMPT_STATUS_NOT_TAKEN_YET"
,
"playerId"
:
"<string>"
,
"playerName"
:
"<string>"
}
]
},
"mainSpreadLine"
:
123
,
"mainTotalLine"
:
123
,
"marketGroupStats"
: [
{
"marketGroupId"
:
"<string>"
,
"line"
:
123
,
"current"
:
123
}
],
"periodScores"
: [
{
"number"
:
123
,
"type"
:
"PERIOD_SCORE_TYPE_REGULATION"
,
"label"
:
"<string>"
,
"scores"
: [
{
"competitorId"
:
"<string>"
,
"score"
:
123
}
]
}
],
"eventId"
:
123
},
"latestGameUpdate"
: {
"id"
:
123
,
"eventId"
:
123
,
"sportradarGameId"
:
"<string>"
,
"type"
:
"<string>"
,
"title"
:
"<string>"
,
"subtitle"
:
"<string>"
,
"subject"
:
"<string>"
,
"team"
:
"<string>"
,
"period"
:
"<string>"
,
"clock"
:
"<string>"
,
"highlightAt"
:
"2023-11-07T05:31:56Z"
,
"createdAt"
:
"2023-11-07T05:31:56Z"
}
},
"sortType"
:
"<string>"
,
"marketGroups"
: [
{
"id"
:
"<string>"
,
"title"
:
"<string>"
,
"subtitle"
:
"<string>"
,
"parentId"
:
"<string>"
,
"order"
:
123
,
"marketIds"
: [
"<string>"
],
"line"
:
123
,
"current"
:
123
,
"searchable"
:
true
,
"showAllThreshold"
:
123
,
"showMarketImages"
:
true
,
"initialCollapsed"
:
true
,
"live"
:
true
}
],
"primaryTag"
: {
"id"
:
"<string>"
,
"label"
:
"<string>"
,
"slug"
:
"<string>"
,
"createdAt"
:
"<string>"
,
"updatedAt"
:
"<string>"
,
"image"
:
"<string>"
,
"tradable"
:
true
,
"league"
: {
"id"
:
123
,
"name"
:
"<string>"
,
"sportId"
:
123
,
"tagId"
:
123
,
"image"
:
"<string>"
,
"resolution"
:
"<string>"
,
"ordering"
:
"<string>"
,
"activeSeriesId"
:
123
,
"isOperational"
:
true
,
"automaticResolution"
:
true
,
"createdAt"
:
"<string>"
,
"slug"
:
"<string>"
,
"abbreviation"
:
"<string>"
},
"sport"
: {
"id"
:
123
,
"name"
:
"<string>"
,
"tagId"
:
123
,
"createdAt"
:
"<string>"
,
"slug"
:
"<string>"
,
"image"
:
"<string>"
},
"parentId"
:
123
,
"subtags"
: [
{}
],
"hub"
: {
"id"
:
"<string>"
,
"title"
:
"<string>"
,
"image"
:
"<string>"
,
"subtitle"
:
"<string>"
,
"icon"
:
"<string>"
,
"status"
:
"HUB_STATUS_ACTIVE"
,
"startTime"
:
"2023-11-07T05:31:56Z"
}
},
"secondaryTag"
: {
"id"
:
"<string>"
,
"label"
:
"<string>"
,
"slug"
:
"<string>"
,
"createdAt"
:
"<string>"
,
"updatedAt"
:
"<string>"
,
"image"
:
"<string>"
,
"tradable"
:
true
,
"league"
: {
"id"
:
123
,
"name"
:
"<string>"
,
"sportId"
:
123
,
"tagId"
:
123
,
"image"
:
"<string>"
,
"resolution"
:
"<string>"
,
"ordering"
:
"<string>"
,
"activeSeriesId"
:
123
,
"isOperational"
:
true
,
"automaticResolution"
:
true
,
"createdAt"
:
"<string>"
,
"slug"
:
"<string>"
,
"abbreviation"
:
"<string>"
},
"sport"
: {
"id"
:
123
,
"name"
:
"<string>"
,
"tagId"
:
123
,
"createdAt"
:
"<string>"
,
"slug"
:
"<string>"
,
"image"
:
"<string>"
},
"parentId"
:
123
,
"subtags"
: [
{}
],
"hub"
: {
"id"
:
"<string>"
,
"title"
:
"<string>"
,
"image"
:
"<string>"
,
"subtitle"
:
"<string>"
,
"icon"
:
"<string>"
,
"status"
:
"HUB_STATUS_ACTIVE"
,
"startTime"
:
"2023-11-07T05:31:56Z"
}
},
"primaryTagSlug"
:
"<string>"
,
"secondaryTagSlug"
:
"<string>"
,
"livestreamUrl"
:
"<string>"
,
"streamProvider"
:
"<string>"
,
"streamRequiresAuth"
:
true
,
"featureAvailability"
: {
"lineups"
:
true
,
"timeline"
:
true
,
"stats"
:
true
},
"combos"
: {
"enabled"
:
true
,
"numMarkets"
:
123
,
"numSpreadsAndTotalsMarkets"
:
123
},
"marketCounts"
: {
"numMarkets"
:
123
,
"numSpreadsAndTotalsMarkets"
:
123
}
}
]
}
GET
/
v1
/
events
Try it
Get Events
cURL
curl
--request
GET
\
--url
https://gateway.polymarket.us/v1/events
import requests
url = "https://gateway.polymarket.us/v1/events"
response = requests.get(url)
print(response.text)
const options = {method: 'GET'};
fetch('https://gateway.polymarket.us/v1/events', options)
.then(res => res.json())
.then(res => console.log(res))
.catch(err => console.error(err));
<?php
$curl = curl_init();
curl_setopt_array($curl, [
CURLOPT_URL => "https://gateway.polymarket.us/v1/events",
CURLOPT_RETURNTRANSFER => true,
CURLOPT_ENCODING => "",
CURLOPT_MAXREDIRS => 10,
CURLOPT_TIMEOUT => 30,
CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
CURLOPT_CUSTOMREQUEST => "GET",
]);
$response = curl_exec($curl);
$err = curl_error($curl);
curl_close($curl);
if ($err) {
echo "cURL Error #:" . $err;
} else {
echo $response;
}
package main
import (
"fmt"
"net/http"
"io"
)
func main() {
url := "https://gateway.polymarket.us/v1/events"
req, _ := http.NewRequest("GET", url, nil)
res, _ := http.DefaultClient.Do(req)
defer res.Body.Close()
body, _ := io.ReadAll(res.Body)
fmt.Println(string(body))
}
HttpResponse<String> response = Unirest.get("https://gateway.polymarket.us/v1/events")
.asString();
require 'uri'
require 'net/http'
url = URI("https://gateway.polymarket.us/v1/events")
http = Net::HTTP.new(url.host, url.port)
http.use_ssl = true
request = Net::HTTP::Get.new(url)
response = http.request(request)
puts response.read_body
200
{
"events"
: [
{
"id"
:
"<string>"
,
"ticker"
:
"<string>"
,
"slug"
:
"<string>"
,
"title"
:
"<string>"
,
"subtitle"
:
"<string>"
,
"description"
:
"<string>"
,
"resolutionSource"
:
"<string>"
,
"startDate"
:
"<string>"
,
"creationDate"
:
"<string>"
,
"endDate"
:
"<string>"
,
"image"
:
"<string>"
,
"imageDisplayType"
:
"IMAGE_DISPLAY_TYPE_HEADSHOT"
,
"active"
:
true
,
"closed"
:
true
,
"archived"
:
true
,
"liquidity"
:
123
,
"volume"
:
123
,
"openInterest"
:
123
,
"category"
:
"<string>"
,
"subcategory"
:
"<string>"
,
"createdAt"
:
"<string>"
,
"updatedAt"
:
"<string>"
,
"volume24hr"
:
123
,
"volume1wk"
:
123
,
"volume1mo"
:
123
,
"volume1yr"
:
123
,
"closedTime"
:
"<string>"
,
"eventDate"
:
"<string>"
,
"startTime"
:
"<string>"
,
"seriesSlug"
:
"<string>"
,
"score"
:
"<string>"
,
"elapsed"
:
"<string>"
,
"period"
:
"<string>"
,
"live"
:
true
,
"ended"
:
true
,
"finishedTimestamp"
:
"<string>"
,
"featuredOrder"
:
123
,
"markets"
: [
{
"id"
:
"<string>"
,
"question"
:
"<string>"
,
"slug"
:
"<string>"
,
"endDate"
:
"<string>"
,
"category"
:
"<string>"
,
"startDate"
:
"<string>"
,
"image"
:
"<string>"
,
"imageDisplayType"
:
"IMAGE_DISPLAY_TYPE_HEADSHOT"
,
"description"
:
"<string>"
,
"active"
:
true
,
"marketType"
:
"<string>"
,
"closed"
:
true
,
"createdAt"
:
"<string>"
,
"updatedAt"
:
"<string>"
,
"archived"
:
true
,
"orderPriceMinTickSize"
:
123
,
"gameStartTime"
:
"<string>"
,
"manualActivation"
:
true
,
"sportsMarketType"
:
"<string>"
,
"line"
:
123
,
"marketSides"
: [
{
"id"
:
"<string>"
,
"marketSideType"
:
"MARKET_SIDE_TYPE_ERC1155"
,
"identifier"
:
"<string>"
,
"createdAt"
:
"<string>"
,
"updatedAt"
:
"<string>"
,
"description"
:
"<string>"
,
"price"
:
"<string>"
,
"marketId"
:
123
,
"long"
:
true
,
"teamId"
:
123
,
"team"
: {
"id"
:
123
,
"name"
:
"<string>"
,
"abbreviation"
:
"<string>"
,
"league"
:
"<string>"
,
"record"
:
"<string>"
,
"logo"
:
"<string>"
,
"alias"
:
"<string>"
,
"safeName"
:
"<string>"
,
"homeIcon"
:
"<string>"
,
"awayIcon"
:
"<string>"
,
"colorPrimary"
:
"<string>"
,
"providerId"
:
123
,
"ordering"
:
"<string>"
,
"longIcon"
:
"<string>"
,
"shortIcon"
:
"<string>"
,
"displayAbbreviation"
:
"<string>"
,
"ranking"
:
"<string>"
,
"conference"
:
"<string>"
,
"providerIds"
: [
{
"provider"
:
"PROVIDER_SPORTSDATAIO"
,
"providerId"
:
"<string>"
}
],
"longIconDark"
:
"<string>"
,
"shortIconDark"
:
"<string>"
,
"color"
: {
"light"
:
"<string>"
,
"dark"
:
"<string>"
},
"imageDisplayType"
:
"IMAGE_DISPLAY_TYPE_HEADSHOT"
},
"quote"
: {
"value"
:
123.45
,
"currency"
:
"<string>"
},
"tradable"
:
true
}
],
"outcomes"
:
"<string>"
,
"outcomePrices"
:
"<string>"
,
"ep3Status"
:
"<string>"
,
"status"
:
"MARKET_STATUS_UNSPECIFIED"
,
"assetPriceTerms"
: {
"marketType"
:
"ASSET_PRICE_MARKET_TYPE_UNSPECIFIED"
,
"asset"
: {
"assetClass"
:
"ASSET_CLASS_CRYPTO"
,
"symbol"
:
"btc"
},
"indexSymbol"
:
"<string>"
,
"horizon"
:
"<string>"
,
"windowStart"
:
"2023-11-07T05:31:56Z"
,
"windowEnd"
:
"2023-11-07T05:31:56Z"
,
"priceToBeat"
: {
"value"
:
123.45
,
"currency"
:
"<string>"
},
"strike"
: {
"value"
:
123.45
,
"currency"
:
"<string>"
},
"rangeLower"
: {
"value"
:
123.45
,
"currency"
:
"<string>"
},
"rangeUpper"
: {
"value"
:
123.45
,
"currency"
:
"<string>"
},
"rangeKind"
:
"ASSET_PRICE_RANGE_KIND_UNSPECIFIED"
,
"direction"
:
"ASSET_PRICE_DIRECTION_UNSPECIFIED"
,
"settlementPrice"
: {
"value"
:
123.45
,
"currency"
:
"<string>"
}
},
"sportsMarketTypeV2"
:
"SPORTS_MARKET_TYPE_MONEYLINE"
,
"hidden"
:
true
,
"tags"
: [
{
"id"
:
"<string>"
,
"label"
:
"<string>"
,
"slug"
:
"<string>"
,
"createdAt"
:
"<string>"
,
"updatedAt"
:
"<string>"
,
"image"
:
"<string>"
,
"tradable"
:
true
,
"league"
: {
"id"
:
123
,
"name"
:
"<string>"
,
"sportId"
:
123
,
"tagId"
:
123
,
"image"
:
"<string>"
,
"resolution"
:
"<string>"
,
"ordering"
:
"<string>"
,
"activeSeriesId"
:
123
,
"isOperational"
:
true
,
"automaticResolution"
:
true
,
"createdAt"
:
"<string>"
,
"slug"
:
"<string>"
,
"abbreviation"
:
"<string>"
},
"sport"
: {
"id"
:
123
,
"name"
:
"<string>"
,
"tagId"
:
123
,
"createdAt"
:
"<string>"
,
"slug"
:
"<string>"
,
"image"
:
"<string>"
},
"parentId"
:
123
,
"subtags"
: [
{}
],
"hub"
: {
"id"
:
"<string>"
,
"title"
:
"<string>"
,
"image"
:
"<string>"
,
"subtitle"
:
"<string>"
,
"icon"
:
"<string>"
,
"status"
:
"HUB_STATUS_ACTIVE"
,
"startTime"
:
"2023-11-07T05:31:56Z"
}
}
],
"title"
:
"<string>"
,
"subtitle"
:
"<string>"
,
"color"
:
"<string>"
,
"darkColor"
:
"<string>"
,
"subjectId"
:
123
,
"subject"
: {
"id"
:
123
,
"name"
:
"<string>"
,
"displayName"
:
"<string>"
,
"description"
:
"<string>"
,
"subjectType"
:
"<string>"
,
"image"
:
"<string>"
,
"color"
:
"<string>"
,
"darkColor"
:
"<string>"
,
"createdAt"
:
"<string>"
,
"updatedAt"
:
"<string>"
,
"slug"
:
"<string>"
},
"feeCoefficient"
:
123
,
"spreadTotalSuffix"
:
"<string>"
,
"sortOrder"
:
123
,
"bestBidQuote"
: {
"value"
:
123.45
,
"currency"
:
"<string>"
},
"bestAskQuote"
: {
"value"
:
123.45
,
"currency"
:
"<string>"
},
"metadata"
: {},
"titleShort"
:
"<string>"
,
"ep3SyncedAt"
:
"<string>"
,
"minimumTradeQty"
:
123
,
"volume"
:
123
,
"volume24hr"
:
123
,
"volume1wk"
:
123
,
"volume1mo"
:
123
,
"volume1yr"
:
123
,
"rulesDisclaimer"
:
"<string>"
,
"rulesDisclaimerPopup"
:
true
,
"comboEnabled"
:
true
}
],
"gameId"
:
123
,
"rescheduledFromGameId"
:
123
,
"sportradarGameId"
:
"<string>"
,
"eventState"
: {
"id"
:
123
,
"gameId"
:
123
,
"sportradarGameId"
:
"<string>"
,
"type"
:
"<string>"
,
"createdAt"
:
"2023-11-07T05:31:56Z"
,
"updatedAt"
:
"2023-11-07T05:31:56Z"
,
"score"
:
"<string>"
,
"elapsed"
:
"<string>"
,
"period"
:
"<string>"
,
"live"
:
true
,
"ended"
:
true
,
"finishedTimestamp"
:
"2023-11-07T05:31:56Z"
,
"footballState"
: {
"down"
:
123
,
"yard"
:
123
,
"possessionProviderId"
:
"<string>"
,
"driveState"
: {
"down"
:
123
,
"yfd"
:
123
,
"possessionTeamId"
:
"<string>"
,
"fieldPosition"
: {
"teamId"
:
"<string>"
,
"yard"
:
123
},
"startFieldPosition"
: {
"teamId"
:
"<string>"
,
"yard"
:
123
}
},
"timeouts"
: [
{
"teamId"
:
"<string>"
,
"used"
:
123
,
"remaining"
:
123
}
]
},
"ufcState"
: {
"weightClass"
:
"<string>"
,
"cardSegment"
:
"<string>"
,
"eventLogo"
:
"<string>"
,
"rounds"
:
123
,
"order"
:
123
},
"tennisState"
: {
"tournamentName"
:
"<string>"
,
"round"
:
"<string>"
,
"servingTeamId"
:
123
},
"baseballState"
: {
"balls"
:
123
,
"strikes"
:
123
,
"outs"
:
123
,
"onFirst"
:
true
,
"onSecond"
:
true
,
"onThird"
:
true
,
"inningHalf"
:
"<string>"
},
"cricketState"
: {
"innings"
: [
{
"number"
:
123
,
"battingTeamId"
:
"<string>"
,
"runs"
:
123
,
"wickets"
:
123
,
"oversCompleted"
:
123
,
"complete"
:
true
,
"ballsIntoOver"
:
123
}
],
"currentInnings"
:
123
,
"totalOvers"
:
123
,
"phase"
:
"<string>"
,
"chase"
: {
"target"
:
123
,
"runsNeeded"
:
123
,
"ballsRemaining"
:
123
,
"currentRunRate"
:
123
,
"requiredRunRate"
:
123
}
},
"soccerState"
: {
"shootoutAttempts"
: [
{
"competitorId"
:
"<string>"
,
"status"
:
"SOCCER_PENALTY_SHOOTOUT_ATTEMPT_STATUS_NOT_TAKEN_YET"
,
"playerId"
:
"<string>"
,
"playerName"
:
"<string>"
}
]
},
"mainSpreadLine"
:
123
,
"mainTotalLine"
:
123
,
"marketGroupStats"
: [
{
"marketGroupId"
:
"<string>"
,
"line"
:
123
,
"current"
:
123
}
],
"periodScores"
: [
{
"number"
:
123
,
"type"
:
"PERIOD_SCORE_TYPE_REGULATION"
,
"label"
:
"<string>"
,
"scores"
: [
{
"competitorId"
:
"<string>"
,
"score"
:
123
}
]
}
],
"eventId"
:
123
},
"hidden"
:
true
,
"tags"
: [
{
"id"
:
"<string>"
,
"label"
:
"<string>"
,
"slug"
:
"<string>"
,
"createdAt"
:
"<string>"
,
"updatedAt"
:
"<string>"
,
"image"
:
"<string>"
,
"tradable"
:
true
,
"league"
: {
"id"
:
123
,
"name"
:
"<string>"
,
"sportId"
:
123
,
"tagId"
:
123
,
"image"
:
"<string>"
,
"resolution"
:
"<string>"
,
"ordering"
:
"<string>"
,
"activeSeriesId"
:
123
,
"isOperational"
:
true
,
"automaticResolution"
:
true
,
"createdAt"
:
"<string>"
,
"slug"
:
"<string>"
,
"abbreviation"
:
"<string>"
},
"sport"
: {
"id"
:
123
,
"name"
:
"<string>"
,
"tagId"
:
123
,
"createdAt"
:
"<string>"
,
"slug"
:
"<string>"
,
"image"
:
"<string>"
},
"parentId"
:
123
,
"subtags"
: [
{}
],
"hub"
: {
"id"
:
"<string>"
,
"title"
:
"<string>"
,
"image"
:
"<string>"
,
"subtitle"
:
"<string>"
,
"icon"
:
"<string>"
,
"status"
:
"HUB_STATUS_ACTIVE"
,
"startTime"
:
"2023-11-07T05:31:56Z"
}
}
],
"teams"
: [
{
"id"
:
123
,
"name"
:
"<string>"
,
"abbreviation"
:
"<string>"
,
"league"
:
"<string>"
,
"record"
:
"<string>"
,
"logo"
:
"<string>"
,
"alias"
:
"<string>"
,
"safeName"
:
"<string>"
,
"homeIcon"
:
"<string>"
,
"awayIcon"
:
"<string>"
,
"colorPrimary"
:
"<string>"
,
"providerId"
:
123
,
"ordering"
:
"<string>"
,
"longIcon"
:
"<string>"
,
"shortIcon"
:
"<string>"
,
"displayAbbreviation"
:
"<string>"
,
"ranking"
:
"<string>"
,
"conference"
:
"<string>"
,
"providerIds"
: [
{
"provider"
:
"PROVIDER_SPORTSDATAIO"
,
"providerId"
:
"<string>"
}
],
"longIconDark"
:
"<string>"
,
"shortIconDark"
:
"<string>"
,
"color"
: {
"light"
:
"<string>"
,
"dark"
:
"<string>"
},
"imageDisplayType"
:
"IMAGE_DISPLAY_TYPE_HEADSHOT"
}
],
"metadata"
: {
"gameState"
: {
"id"
:
123
,
"gameId"
:
123
,
"sportradarGameId"
:
"<string>"
,
"type"
:
"<string>"
,
"createdAt"
:
"2023-11-07T05:31:56Z"
,
"updatedAt"
:
"2023-11-07T05:31:56Z"
,
"score"
:
"<string>"
,
"elapsed"
:
"<string>"
,
"period"
:
"<string>"
,
"live"
:
true
,
"ended"
:
true
,
"finishedTimestamp"
:
"2023-11-07T05:31:56Z"
,
"footballState"
: {
"down"
:
123
,
"yard"
:
123
,
"possessionProviderId"
:
"<string>"
,
"driveState"
: {
"down"
:
123
,
"yfd"
:
123
,
"possessionTeamId"
:
"<string>"
,
"fieldPosition"
: {
"teamId"
:
"<string>"
,
"yard"
:
123
},
"startFieldPosition"
: {
"teamId"
:
"<string>"
,
"yard"
:
123
}
},
"timeouts"
: [
{
"teamId"
:
"<string>"
,
"used"
:
123
,
"remaining"
:
123
}
]
},
"ufcState"
: {
"weightClass"
:
"<string>"
,
"cardSegment"
:
"<string>"
,
"eventLogo"
:
"<string>"
,
"rounds"
:
123
,
"order"
:
123
},
"tennisState"
: {
"tournamentName"
:
"<string>"
,
"round"
:
"<string>"
,
"servingTeamId"
:
123
},
"baseballState"
: {
"balls"
:
123
,
"strikes"
:
123
,
"outs"
:
123
,
"onFirst"
:
true
,
"onSecond"
:
true
,
"onThird"
:
true
,
"inningHalf"
:
"<string>"
},
"cricketState"
: {
"innings"
: [
{
"number"
:
123
,
"battingTeamId"
:
"<string>"
,
"runs"
:
123
,
"wickets"
:
123
,
"oversCompleted"
:
123
,
"complete"
:
true
,
"ballsIntoOver"
:
123
}
],
"currentInnings"
:
123
,
"totalOvers"
:
123
,
"phase"
:
"<string>"
,
"chase"
: {
"target"
:
123
,
"runsNeeded"
:
123
,
"ballsRemaining"
:
123
,
"currentRunRate"
:
123
,
"requiredRunRate"
:
123
}
},
"soccerState"
: {
"shootoutAttempts"
: [
{
"competitorId"
:
"<string>"
,
"status"
:
"SOCCER_PENALTY_SHOOTOUT_ATTEMPT_STATUS_NOT_TAKEN_YET"
,
"playerId"
:
"<string>"
,
"playerName"
:
"<string>"
}
]
},
"mainSpreadLine"
:
123
,
"mainTotalLine"
:
123
,
"marketGroupStats"
: [
{
"marketGroupId"
:
"<string>"
,
"line"
:
123
,
"current"
:
123
}
],
"periodScores"
: [
{
"number"
:
123
,
"type"
:
"PERIOD_SCORE_TYPE_REGULATION"
,
"label"
:
"<string>"
,
"scores"
: [
{
"competitorId"
:
"<string>"
,
"score"
:
123
}
]
}
],
"eventId"
:
123
},
"latestGameUpdate"
: {
"id"
:
123
,
"eventId"
:
123
,
"sportradarGameId"
:
"<string>"
,
"type"
:
"<string>"
,
"title"
:
"<string>"
,
"subtitle"
:
"<string>"
,
"subject"
:
"<string>"
,
"team"
:
"<string>"
,
"period"
:
"<string>"
,
"clock"
:
"<string>"
,
"highlightAt"
:
"2023-11-07T05:31:56Z"
,
"createdAt"
:
"2023-11-07T05:31:56Z"
}
},
"sortType"
:
"<string>"
,
"marketGroups"
: [
{
"id"
:
"<string>"
,
"title"
:
"<string>"
,
"subtitle"
:
"<string>"
,
"parentId"
:
"<string>"
,
"order"
:
123
,
"marketIds"
: [
"<string>"
],
"line"
:
123
,
"current"
:
123
,
"searchable"
:
true
,
"showAllThreshold"
:
123
,
"showMarketImages"
:
true
,
"initialCollapsed"
:
true
,
"live"
:
true
}
],
"primaryTag"
: {
"id"
:
"<string>"
,
"label"
:
"<string>"
,
"slug"
:
"<string>"
,
"createdAt"
:
"<string>"
,
"updatedAt"
:
"<string>"
,
"image"
:
"<string>"
,
"tradable"
:
true
,
"league"
: {
"id"
:
123
,
"name"
:
"<string>"
,
"sportId"
:
123
,
"tagId"
:
123
,
"image"
:
"<string>"
,
"resolution"
:
"<string>"
,
"ordering"
:
"<string>"
,
"activeSeriesId"
:
123
,
"isOperational"
:
true
,
"automaticResolution"
:
true
,
"createdAt"
:
"<string>"
,
"slug"
:
"<string>"
,
"abbreviation"
:
"<string>"
},
"sport"
: {
"id"
:
123
,
"name"
:
"<string>"
,
"tagId"
:
123
,
"createdAt"
:
"<string>"
,
"slug"
:
"<string>"
,
"image"
:
"<string>"
},
"parentId"
:
123
,
"subtags"
: [
{}
],
"hub"
: {
"id"
:
"<string>"
,
"title"
:
"<string>"
,
"image"
:
"<string>"
,
"subtitle"
:
"<string>"
,
"icon"
:
"<string>"
,
"status"
:
"HUB_STATUS_ACTIVE"
,
"startTime"
:
"2023-11-07T05:31:56Z"
}
},
"secondaryTag"
: {
"id"
:
"<string>"
,
"label"
:
"<string>"
,
"slug"
:
"<string>"
,
"createdAt"
:
"<string>"
,
"updatedAt"
:
"<string>"
,
"image"
:
"<string>"
,
"tradable"
:
true
,
"league"
: {
"id"
:
123
,
"name"
:
"<string>"
,
"sportId"
:
123
,
"tagId"
:
123
,
"image"
:
"<string>"
,
"resolution"
:
"<string>"
,
"ordering"
:
"<string>"
,
"activeSeriesId"
:
123
,
"isOperational"
:
true
,
"automaticResolution"
:
true
,
"createdAt"
:
"<string>"
,
"slug"
:
"<string>"
,
"abbreviation"
:
"<string>"
},
"sport"
: {
"id"
:
123
,
"name"
:
"<string>"
,
"tagId"
:
123
,
"createdAt"
:
"<string>"
,
"slug"
:
"<string>"
,
"image"
:
"<string>"
},
"parentId"
:
123
,
"subtags"
: [
{}
],
"hub"
: {
"id"
:
"<string>"
,
"title"
:
"<string>"
,
"image"
:
"<string>"
,
"subtitle"
:
"<string>"
,
"icon"
:
"<string>"
,
"status"
:
"HUB_STATUS_ACTIVE"
,
"startTime"
:
"2023-11-07T05:31:56Z"
}
},
"primaryTagSlug"
:
"<string>"
,
"secondaryTagSlug"
:
"<string>"
,
"livestreamUrl"
:
"<string>"
,
"streamProvider"
:
"<string>"
,
"streamRequiresAuth"
:
true
,
"featureAvailability"
: {
"lineups"
:
true
,
"timeline"
:
true
,
"stats"
:
true
},
"combos"
: {
"enabled"
:
true
,
"numMarkets"
:
123
,
"numSpreadsAndTotalsMarkets"
:
123
},
"marketCounts"
: {
"numMarkets"
:
123
,
"numSpreadsAndTotalsMarkets"
:
123
}
}
]
}
Query Parameters
​
limit
integer<int32>
Maximum number of events to return
​
offset
integer<int32>
Number of events to skip for pagination
​
orderBy
string[]
Fields to order results by
​
orderDirection
string
Order direction (asc or desc)
​
id
integer<int32>[]
Filter by event IDs
​
slug
string[]
Filter by event slugs
​
archived
boolean
Filter by archived status
​
active
boolean
Filter by active status
​
closed
boolean
Filter by closed status
​
liquidityMin
number<double>
Minimum liquidity filter
​
liquidityMax
number<double>
Maximum liquidity filter
​
volumeMin
number<double>
Minimum volume filter
​
volumeMax
number<double>
Maximum volume filter
​
startDateMin
string
Minimum start date filter
​
startDateMax
string
Maximum start date filter
​
endDateMin
string
Minimum end date filter
​
endDateMax
string
Maximum end date filter
​
relatedTags
boolean
Include related tags
​
tagSlug
string
Filter by tag slug
​
userId
string
Filter by user ID
​
featured
boolean
Filter by featured status
​
seriesId
integer<int32>[]
Filter by series IDs
​
eventDate
string
Filter by event date
​
startTimeMin
string
Minimum start time filter
​
startTimeMax
string
Maximum start time filter
​
excludeTagId
integer<int32>[]
Tag IDs to exclude
​
featuredOrder
boolean
Order by featured position
​
includeTemplate
boolean
Include template events
​
recurrence
string
Filter by recurrence type
​
gameId
integer<int32>
Filter by game ID
​
rescheduledFromGameId
integer<int32>
Filter by rescheduled from game ID
​
period
string
Filter by event period
​
finishedTimestampMin
string
Minimum finished timestamp filter
​
finishedTimestampMax
string
Maximum finished timestamp filter
​
ended
boolean
Filter by ended status
​
sportradarGameId
string
Filter by Sportradar game ID
​
excludeSeriesId
integer<int32>[]
Series IDs to exclude
​
resolution
boolean
Filter by resolution status
​
categories
string[]
Filter by categories
​
marketTypes
string[]
Filter by market types
​
live
boolean
Filter by live status
​
excludeEventId
integer<int32>[]
Event IDs to exclude
​
includeHidden
boolean
Include hidden events (default: false)
​
tagIds
integer<int32>[]
Filter by tag IDs
​
sportsMarketTypes
string[]
Filter by fine-grained sports_market_type (e.g. moneyline, drawable_outcome, soccer_game_to_advance)
​
includeComboMarketCounts
boolean
Include derived event-level combo market counts
​
teamId
integer<int32>
Filter to events the team participates in
​
tagSlugsAll
string[]
Events must carry every one of these tag slugs (AND). Contrast tag_slug (single) and tag_ids (OR)
​
includePopularPlayerProps
boolean
Include the synthetic Popular section in Player Props market groups
Response
200
application/json
List of events
Response containing list of events
​
events
object[]
List of events
Show
child attributes
```

## Section: Markets
---

### Get Market By Slug (GET)
**Source Routing Target:** https://docs.polymarket.us/api-reference/markets/get-by-slug

```text
ERROR: Status code 404
```

### Get Price History (GET)
**Source Routing Target:** https://docs.polymarket.us/api-reference/markets/get-price-history

```text
ERROR: Status code 404
```

### Get Market By ID (GET)
**Source Routing Target:** https://docs.polymarket.us/api-reference/markets/get-by-id

```text
ERROR: Status code 404
```

### Markets API Overview
**Source Routing Target:** https://docs.polymarket.us/api-reference/markets/overview

```text
ERROR: Status code 404
```

### Get Markets (GET)
**Source Routing Target:** https://docs.polymarket.us/api-reference/markets/get-markets

```text
Get Markets
cURL
curl
--request
GET
\
--url
https://gateway.polymarket.us/v1/markets
import requests
url = "https://gateway.polymarket.us/v1/markets"
response = requests.get(url)
print(response.text)
const options = {method: 'GET'};
fetch('https://gateway.polymarket.us/v1/markets', options)
.then(res => res.json())
.then(res => console.log(res))
.catch(err => console.error(err));
<?php
$curl = curl_init();
curl_setopt_array($curl, [
CURLOPT_URL => "https://gateway.polymarket.us/v1/markets",
CURLOPT_RETURNTRANSFER => true,
CURLOPT_ENCODING => "",
CURLOPT_MAXREDIRS => 10,
CURLOPT_TIMEOUT => 30,
CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
CURLOPT_CUSTOMREQUEST => "GET",
]);
$response = curl_exec($curl);
$err = curl_error($curl);
curl_close($curl);
if ($err) {
echo "cURL Error #:" . $err;
} else {
echo $response;
}
package main
import (
"fmt"
"net/http"
"io"
)
func main() {
url := "https://gateway.polymarket.us/v1/markets"
req, _ := http.NewRequest("GET", url, nil)
res, _ := http.DefaultClient.Do(req)
defer res.Body.Close()
body, _ := io.ReadAll(res.Body)
fmt.Println(string(body))
}
HttpResponse<String> response = Unirest.get("https://gateway.polymarket.us/v1/markets")
.asString();
require 'uri'
require 'net/http'
url = URI("https://gateway.polymarket.us/v1/markets")
http = Net::HTTP.new(url.host, url.port)
http.use_ssl = true
request = Net::HTTP::Get.new(url)
response = http.request(request)
puts response.read_body
200
{
"markets"
: [
{
"id"
:
"<string>"
,
"question"
:
"<string>"
,
"slug"
:
"<string>"
,
"endDate"
:
"<string>"
,
"category"
:
"<string>"
,
"startDate"
:
"<string>"
,
"image"
:
"<string>"
,
"imageDisplayType"
:
"IMAGE_DISPLAY_TYPE_HEADSHOT"
,
"description"
:
"<string>"
,
"active"
:
true
,
"marketType"
:
"<string>"
,
"closed"
:
true
,
"createdAt"
:
"<string>"
,
"updatedAt"
:
"<string>"
,
"archived"
:
true
,
"orderPriceMinTickSize"
:
123
,
"gameStartTime"
:
"<string>"
,
"manualActivation"
:
true
,
"sportsMarketType"
:
"<string>"
,
"line"
:
123
,
"marketSides"
: [
{
"id"
:
"<string>"
,
"marketSideType"
:
"MARKET_SIDE_TYPE_ERC1155"
,
"identifier"
:
"<string>"
,
"createdAt"
:
"<string>"
,
"updatedAt"
:
"<string>"
,
"description"
:
"<string>"
,
"price"
:
"<string>"
,
"marketId"
:
123
,
"long"
:
true
,
"teamId"
:
123
,
"team"
: {
"id"
:
123
,
"name"
:
"<string>"
,
"abbreviation"
:
"<string>"
,
"league"
:
"<string>"
,
"record"
:
"<string>"
,
"logo"
:
"<string>"
,
"alias"
:
"<string>"
,
"safeName"
:
"<string>"
,
"homeIcon"
:
"<string>"
,
"awayIcon"
:
"<string>"
,
"colorPrimary"
:
"<string>"
,
"providerId"
:
123
,
"ordering"
:
"<string>"
,
"longIcon"
:
"<string>"
,
"shortIcon"
:
"<string>"
,
"displayAbbreviation"
:
"<string>"
,
"ranking"
:
"<string>"
,
"conference"
:
"<string>"
,
"providerIds"
: [
{
"provider"
:
"PROVIDER_SPORTSDATAIO"
,
"providerId"
:
"<string>"
}
],
"longIconDark"
:
"<string>"
,
"shortIconDark"
:
"<string>"
,
"color"
: {
"light"
:
"<string>"
,
"dark"
:
"<string>"
},
"imageDisplayType"
:
"IMAGE_DISPLAY_TYPE_HEADSHOT"
},
"quote"
: {
"value"
:
123.45
,
"currency"
:
"<string>"
},
"tradable"
:
true
}
],
"outcomes"
:
"<string>"
,
"outcomePrices"
:
"<string>"
,
"ep3Status"
:
"<string>"
,
"status"
:
"MARKET_STATUS_UNSPECIFIED"
,
"assetPriceTerms"
: {
"marketType"
:
"ASSET_PRICE_MARKET_TYPE_UNSPECIFIED"
,
"asset"
: {
"assetClass"
:
"ASSET_CLASS_CRYPTO"
,
"symbol"
:
"btc"
},
"indexSymbol"
:
"<string>"
,
"horizon"
:
"<string>"
,
"windowStart"
:
"2023-11-07T05:31:56Z"
,
"windowEnd"
:
"2023-11-07T05:31:56Z"
,
"priceToBeat"
: {
"value"
:
123.45
,
"currency"
:
"<string>"
},
"strike"
: {
"value"
:
123.45
,
"currency"
:
"<string>"
},
"rangeLower"
: {
"value"
:
123.45
,
"currency"
:
"<string>"
},
"rangeUpper"
: {
"value"
:
123.45
,
"currency"
:
"<string>"
},
"rangeKind"
:
"ASSET_PRICE_RANGE_KIND_UNSPECIFIED"
,
"direction"
:
"ASSET_PRICE_DIRECTION_UNSPECIFIED"
,
"settlementPrice"
: {
"value"
:
123.45
,
"currency"
:
"<string>"
}
},
"sportsMarketTypeV2"
:
"SPORTS_MARKET_TYPE_MONEYLINE"
,
"hidden"
:
true
,
"tags"
: [
{
"id"
:
"<string>"
,
"label"
:
"<string>"
,
"slug"
:
"<string>"
,
"createdAt"
:
"<string>"
,
"updatedAt"
:
"<string>"
,
"image"
:
"<string>"
,
"tradable"
:
true
,
"league"
: {
"id"
:
123
,
"name"
:
"<string>"
,
"sportId"
:
123
,
"tagId"
:
123
,
"image"
:
"<string>"
,
"resolution"
:
"<string>"
,
"ordering"
:
"<string>"
,
"activeSeriesId"
:
123
,
"isOperational"
:
true
,
"automaticResolution"
:
true
,
"createdAt"
:
"<string>"
,
"slug"
:
"<string>"
,
"abbreviation"
:
"<string>"
},
"sport"
: {
"id"
:
123
,
"name"
:
"<string>"
,
"tagId"
:
123
,
"createdAt"
:
"<string>"
,
"slug"
:
"<string>"
,
"image"
:
"<string>"
},
"parentId"
:
123
,
"subtags"
: [
{}
],
"hub"
: {
"id"
:
"<string>"
,
"title"
:
"<string>"
,
"image"
:
"<string>"
,
"subtitle"
:
"<string>"
,
"icon"
:
"<string>"
,
"status"
:
"HUB_STATUS_ACTIVE"
,
"startTime"
:
"2023-11-07T05:31:56Z"
}
}
],
"title"
:
"<string>"
,
"subtitle"
:
"<string>"
,
"color"
:
"<string>"
,
"darkColor"
:
"<string>"
,
"subjectId"
:
123
,
"subject"
: {
"id"
:
123
,
"name"
:
"<string>"
,
"displayName"
:
"<string>"
,
"description"
:
"<string>"
,
"subjectType"
:
"<string>"
,
"image"
:
"<string>"
,
"color"
:
"<string>"
,
"darkColor"
:
"<string>"
,
"createdAt"
:
"<string>"
,
"updatedAt"
:
"<string>"
,
"slug"
:
"<string>"
},
"feeCoefficient"
:
123
,
"spreadTotalSuffix"
:
"<string>"
,
"sortOrder"
:
123
,
"bestBidQuote"
: {
"value"
:
123.45
,
"currency"
:
"<string>"
},
"bestAskQuote"
: {
"value"
:
123.45
,
"currency"
:
"<string>"
},
"metadata"
: {},
"titleShort"
:
"<string>"
,
"ep3SyncedAt"
:
"<string>"
,
"minimumTradeQty"
:
123
,
"volume"
:
123
,
"volume24hr"
:
123
,
"volume1wk"
:
123
,
"volume1mo"
:
123
,
"volume1yr"
:
123
,
"rulesDisclaimer"
:
"<string>"
,
"rulesDisclaimerPopup"
:
true
,
"comboEnabled"
:
true
}
]
}
GET
/
v1
/
markets
Try it
Get Markets
cURL
curl
--request
GET
\
--url
https://gateway.polymarket.us/v1/markets
import requests
url = "https://gateway.polymarket.us/v1/markets"
response = requests.get(url)
print(response.text)
const options = {method: 'GET'};
fetch('https://gateway.polymarket.us/v1/markets', options)
.then(res => res.json())
.then(res => console.log(res))
.catch(err => console.error(err));
<?php
$curl = curl_init();
curl_setopt_array($curl, [
CURLOPT_URL => "https://gateway.polymarket.us/v1/markets",
CURLOPT_RETURNTRANSFER => true,
CURLOPT_ENCODING => "",
CURLOPT_MAXREDIRS => 10,
CURLOPT_TIMEOUT => 30,
CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
CURLOPT_CUSTOMREQUEST => "GET",
]);
$response = curl_exec($curl);
$err = curl_error($curl);
curl_close($curl);
if ($err) {
echo "cURL Error #:" . $err;
} else {
echo $response;
}
package main
import (
"fmt"
"net/http"
"io"
)
func main() {
url := "https://gateway.polymarket.us/v1/markets"
req, _ := http.NewRequest("GET", url, nil)
res, _ := http.DefaultClient.Do(req)
defer res.Body.Close()
body, _ := io.ReadAll(res.Body)
fmt.Println(string(body))
}
HttpResponse<String> response = Unirest.get("https://gateway.polymarket.us/v1/markets")
.asString();
require 'uri'
require 'net/http'
url = URI("https://gateway.polymarket.us/v1/markets")
http = Net::HTTP.new(url.host, url.port)
http.use_ssl = true
request = Net::HTTP::Get.new(url)
response = http.request(request)
puts response.read_body
200
{
"markets"
: [
{
"id"
:
"<string>"
,
"question"
:
"<string>"
,
"slug"
:
"<string>"
,
"endDate"
:
"<string>"
,
"category"
:
"<string>"
,
"startDate"
:
"<string>"
,
"image"
:
"<string>"
,
"imageDisplayType"
:
"IMAGE_DISPLAY_TYPE_HEADSHOT"
,
"description"
:
"<string>"
,
"active"
:
true
,
"marketType"
:
"<string>"
,
"closed"
:
true
,
"createdAt"
:
"<string>"
,
"updatedAt"
:
"<string>"
,
"archived"
:
true
,
"orderPriceMinTickSize"
:
123
,
"gameStartTime"
:
"<string>"
,
"manualActivation"
:
true
,
"sportsMarketType"
:
"<string>"
,
"line"
:
123
,
"marketSides"
: [
{
"id"
:
"<string>"
,
"marketSideType"
:
"MARKET_SIDE_TYPE_ERC1155"
,
"identifier"
:
"<string>"
,
"createdAt"
:
"<string>"
,
"updatedAt"
:
"<string>"
,
"description"
:
"<string>"
,
"price"
:
"<string>"
,
"marketId"
:
123
,
"long"
:
true
,
"teamId"
:
123
,
"team"
: {
"id"
:
123
,
"name"
:
"<string>"
,
"abbreviation"
:
"<string>"
,
"league"
:
"<string>"
,
"record"
:
"<string>"
,
"logo"
:
"<string>"
,
"alias"
:
"<string>"
,
"safeName"
:
"<string>"
,
"homeIcon"
:
"<string>"
,
"awayIcon"
:
"<string>"
,
"colorPrimary"
:
"<string>"
,
"providerId"
:
123
,
"ordering"
:
"<string>"
,
"longIcon"
:
"<string>"
,
"shortIcon"
:
"<string>"
,
"displayAbbreviation"
:
"<string>"
,
"ranking"
:
"<string>"
,
"conference"
:
"<string>"
,
"providerIds"
: [
{
"provider"
:
"PROVIDER_SPORTSDATAIO"
,
"providerId"
:
"<string>"
}
],
"longIconDark"
:
"<string>"
,
"shortIconDark"
:
"<string>"
,
"color"
: {
"light"
:
"<string>"
,
"dark"
:
"<string>"
},
"imageDisplayType"
:
"IMAGE_DISPLAY_TYPE_HEADSHOT"
},
"quote"
: {
"value"
:
123.45
,
"currency"
:
"<string>"
},
"tradable"
:
true
}
],
"outcomes"
:
"<string>"
,
"outcomePrices"
:
"<string>"
,
"ep3Status"
:
"<string>"
,
"status"
:
"MARKET_STATUS_UNSPECIFIED"
,
"assetPriceTerms"
: {
"marketType"
:
"ASSET_PRICE_MARKET_TYPE_UNSPECIFIED"
,
"asset"
: {
"assetClass"
:
"ASSET_CLASS_CRYPTO"
,
"symbol"
:
"btc"
},
"indexSymbol"
:
"<string>"
,
"horizon"
:
"<string>"
,
"windowStart"
:
"2023-11-07T05:31:56Z"
,
"windowEnd"
:
"2023-11-07T05:31:56Z"
,
"priceToBeat"
: {
"value"
:
123.45
,
"currency"
:
"<string>"
},
"strike"
: {
"value"
:
123.45
,
"currency"
:
"<string>"
},
"rangeLower"
: {
"value"
:
123.45
,
"currency"
:
"<string>"
},
"rangeUpper"
: {
"value"
:
123.45
,
"currency"
:
"<string>"
},
"rangeKind"
:
"ASSET_PRICE_RANGE_KIND_UNSPECIFIED"
,
"direction"
:
"ASSET_PRICE_DIRECTION_UNSPECIFIED"
,
"settlementPrice"
: {
"value"
:
123.45
,
"currency"
:
"<string>"
}
},
"sportsMarketTypeV2"
:
"SPORTS_MARKET_TYPE_MONEYLINE"
,
"hidden"
:
true
,
"tags"
: [
{
"id"
:
"<string>"
,
"label"
:
"<string>"
,
"slug"
:
"<string>"
,
"createdAt"
:
"<string>"
,
"updatedAt"
:
"<string>"
,
"image"
:
"<string>"
,
"tradable"
:
true
,
"league"
: {
"id"
:
123
,
"name"
:
"<string>"
,
"sportId"
:
123
,
"tagId"
:
123
,
"image"
:
"<string>"
,
"resolution"
:
"<string>"
,
"ordering"
:
"<string>"
,
"activeSeriesId"
:
123
,
"isOperational"
:
true
,
"automaticResolution"
:
true
,
"createdAt"
:
"<string>"
,
"slug"
:
"<string>"
,
"abbreviation"
:
"<string>"
},
"sport"
: {
"id"
:
123
,
"name"
:
"<string>"
,
"tagId"
:
123
,
"createdAt"
:
"<string>"
,
"slug"
:
"<string>"
,
"image"
:
"<string>"
},
"parentId"
:
123
,
"subtags"
: [
{}
],
"hub"
: {
"id"
:
"<string>"
,
"title"
:
"<string>"
,
"image"
:
"<string>"
,
"subtitle"
:
"<string>"
,
"icon"
:
"<string>"
,
"status"
:
"HUB_STATUS_ACTIVE"
,
"startTime"
:
"2023-11-07T05:31:56Z"
}
}
],
"title"
:
"<string>"
,
"subtitle"
:
"<string>"
,
"color"
:
"<string>"
,
"darkColor"
:
"<string>"
,
"subjectId"
:
123
,
"subject"
: {
"id"
:
123
,
"name"
:
"<string>"
,
"displayName"
:
"<string>"
,
"description"
:
"<string>"
,
"subjectType"
:
"<string>"
,
"image"
:
"<string>"
,
"color"
:
"<string>"
,
"darkColor"
:
"<string>"
,
"createdAt"
:
"<string>"
,
"updatedAt"
:
"<string>"
,
"slug"
:
"<string>"
},
"feeCoefficient"
:
123
,
"spreadTotalSuffix"
:
"<string>"
,
"sortOrder"
:
123
,
"bestBidQuote"
: {
"value"
:
123.45
,
"currency"
:
"<string>"
},
"bestAskQuote"
: {
"value"
:
123.45
,
"currency"
:
"<string>"
},
"metadata"
: {},
"titleShort"
:
"<string>"
,
"ep3SyncedAt"
:
"<string>"
,
"minimumTradeQty"
:
123
,
"volume"
:
123
,
"volume24hr"
:
123
,
"volume1wk"
:
123
,
"volume1mo"
:
123
,
"volume1yr"
:
123
,
"rulesDisclaimer"
:
"<string>"
,
"rulesDisclaimerPopup"
:
true
,
"comboEnabled"
:
true
}
]
}
Query Parameters
​
limit
integer<int32>
Page size
​
offset
integer<int32>
Page offset
​
orderBy
string[]
Order by fields
​
orderDirection
string
Order direction
​
id
integer<int32>[]
Market IDs
​
slug
string[]
Market slugs
​
archived
boolean
Whether market is archived
​
active
boolean
Whether market is active
​
closed
boolean
Whether market is closed
​
volumeNumMin
number<double>
Minimum volume number
​
volumeNumMax
number<double>
Maximum volume number
​
startDateMin
string
Minimum start date
​
startDateMax
string
Maximum start date
​
endDateMin
string
Minimum end date
​
endDateMax
string
Maximum end date
​
relatedTags
boolean
Whether related tags are enabled
​
gameId
string
Game ID
​
sportsMarketTypes
enum<string>[]
Sports market types
Available options
:
SPORTS_MARKET_TYPE_MONEYLINE
,
SPORTS_MARKET_TYPE_SPREAD
,
SPORTS_MARKET_TYPE_TOTAL
,
SPORTS_MARKET_TYPE_PROP
,
SPORTS_MARKET_TYPE_FUTURE
,
SPORTS_MARKET_TYPE_DRAWABLE_OUTCOME
​
includeTag
boolean
Whether to include tag
​
categories
string[]
Categories
​
marketTypes
string[]
Market types
​
includeHidden
boolean
Include hidden markets (default: false)
​
tagIds
integer<int32>[]
Tag IDs
Response
200
application/json
List of markets
Response containing list of markets
​
markets
object[]
List of markets
Show
child attributes
```

### Get Market BBO (GET)
**Source Routing Target:** https://docs.polymarket.us/api-reference/markets/get-bbo

```text
ERROR: Status code 404
```

### Get Market Book (GET)
**Source Routing Target:** https://docs.polymarket.us/api-reference/markets/get-book

```text
ERROR: Status code 404
```

### Get Market Settlement (GET)
**Source Routing Target:** https://docs.polymarket.us/api-reference/markets/get-settlement

```text
ERROR: Status code 404
```

## Section: Asset Prices
---

### Asset Prices API Overview
**Source Routing Target:** https://docs.polymarket.us/api-reference/asset-prices/overview

```text
​
Asset Prices API
The Asset Prices API returns the reference index prices that crypto price markets settle on, as OHLC candles. Use it to chart the index next to an Up/Down or ladder market, to seed a live price display, or to check a market’s
priceToBeat
and
settlementPrice
against the index.
​
Endpoints
Method
Endpoint
Description
GET
/v1/asset-prices/history
Bucketed OHLC index price series for one or more assets
No authentication is required.
​
Query Parameters
Parameter
Type
Description
assets
string[]
Assets in canonical
<class>:<symbol>
form, e.g.
crypto:btc
. Repeat the parameter for several assets (
?assets=crypto:btc&assets=crypto:eth
), at most 10. This is the same value as
assetPriceTerms.asset
on a market.
from
integer (unix seconds)
Required. Start of the window. Aligned down to the bucket, and raised when the window would hold more than 3600 candles.
to
integer (unix seconds)
End of the window.
0
or a future value means now; the in-progress bucket is included.
bucket
enum
Required candle width:
ASSET_PRICE_BUCKET_1S
,
_5S
,
_15S
,
_1M
,
_5M
,
_15M
,
_1H
,
_1D
.
The 3600-candle cap is the only size limit, so the widest window scales with the bucket: an hour at
1S
, 60 hours at
1M
, 150 days at
1H
. The effective
from
and
to
after alignment are echoed on each series.
​
Example
GET
/v1/asset-prices/history?assets=crypto:btc
&
from
=
1789949700
&
to
=
1789950600
&
bucket
=
ASSET_PRICE_BUCKET_1M
{
"series"
: [
{
"asset"
: {
"assetClass"
:
"ASSET_CLASS_CRYPTO"
,
"symbol"
:
"btc"
},
"currency"
:
"USD"
,
"bucket"
:
"ASSET_PRICE_BUCKET_1M"
,
"from"
:
1789949700
,
"to"
:
1789950600
,
"candles"
: [
{
"timestamp"
:
1789949700
,
"open"
:
"81646.93"
,
"high"
:
"81690.04"
,
"low"
:
"81633.83"
,
"close"
:
"81653.35"
,
"tickCount"
:
60
},
{
"timestamp"
:
1789949760
,
"open"
:
"81659.13"
,
"high"
:
"81709.62"
,
"low"
:
"81536.86"
,
"close"
:
"81537.63"
,
"tickCount"
:
60
}
]
}
]
}
​
Response Fields
Field
Type
Description
series[].asset
object
The asset this series belongs to. Match series to your request by this field, never by position: REST returns series sorted by symbol.
series[].currency
string
ISO 4217 currency every candle price is quoted in
series[].bucket
enum
Candle width of the series
series[].from
/
series[].to
integer
Effective window bounds (unix seconds) after alignment and clamping
series[].candles[].timestamp
integer
Bucket start (unix seconds)
series[].candles[].open
/
high
/
low
/
close
string (decimal)
Index prices in the bucket, as decimal strings
series[].candles[].tickCount
integer
Number of index publications in the bucket.
0
marks a gap-filled bucket:
close
is carried forward from the previous bucket and
open
,
high
and
low
equal it.
Candles are dense and ascending, one per bucket in the effective window. An unknown symbol in a known class returns an empty series rather than an error.
​
Relationship to Markets
assetPriceTerms.asset
on a crypto market is the
assets
value to chart against.
An Up/Down market’s
priceToBeat
is the simple average of the 60 one-second prices from 59 seconds before
windowStart
up to and including
windowStart
itself, the inclusive interval
[T − 59 s, T]
; its
settlementPrice
is the same statistic at
windowEnd
. The reading exactly at the boundary is part of the average and the reading 60 seconds before it is not. To reproduce it, query
bucket=ASSET_PRICE_BUCKET_1S
with
from = T − 59
and
to = T
and average the 60
close
values. For
cpc-btc-updown-15m-2026-09-21-0015z
, the candles from 00:14:01 to 00:15:00 inclusive average to the published
priceToBeat
of 81650.14; the minute 00:14:00 to 00:14:59 averages to 81649.14 and does not match.
Poll the latest candle for a live price display. Prices are published about once per second.
Index price history is available in the preprod environment today and becomes available in production together with the automated crypto markets, as announced in the
changelog
.
```

### Get A Bucketed OHLC Price Series For One Or More Assets (GET)
**Source Routing Target:** https://docs.polymarket.us/api-reference/asset-prices/get-ohlc

```text
ERROR: Status code 404
```

## Section: Series
---

### Get Series (GET)
**Source Routing Target:** https://docs.polymarket.us/api-reference/series/get-series

```text
Get Series
cURL
curl
--request
GET
\
--url
https://gateway.polymarket.us/v1/series
import requests
url = "https://gateway.polymarket.us/v1/series"
response = requests.get(url)
print(response.text)
const options = {method: 'GET'};
fetch('https://gateway.polymarket.us/v1/series', options)
.then(res => res.json())
.then(res => console.log(res))
.catch(err => console.error(err));
<?php
$curl = curl_init();
curl_setopt_array($curl, [
CURLOPT_URL => "https://gateway.polymarket.us/v1/series",
CURLOPT_RETURNTRANSFER => true,
CURLOPT_ENCODING => "",
CURLOPT_MAXREDIRS => 10,
CURLOPT_TIMEOUT => 30,
CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
CURLOPT_CUSTOMREQUEST => "GET",
]);
$response = curl_exec($curl);
$err = curl_error($curl);
curl_close($curl);
if ($err) {
echo "cURL Error #:" . $err;
} else {
echo $response;
}
package main
import (
"fmt"
"net/http"
"io"
)
func main() {
url := "https://gateway.polymarket.us/v1/series"
req, _ := http.NewRequest("GET", url, nil)
res, _ := http.DefaultClient.Do(req)
defer res.Body.Close()
body, _ := io.ReadAll(res.Body)
fmt.Println(string(body))
}
HttpResponse<String> response = Unirest.get("https://gateway.polymarket.us/v1/series")
.asString();
require 'uri'
require 'net/http'
url = URI("https://gateway.polymarket.us/v1/series")
http = Net::HTTP.new(url.host, url.port)
http.use_ssl = true
request = Net::HTTP::Get.new(url)
response = http.request(request)
puts response.read_body
200
{
"series"
: [
{
"id"
:
"<string>"
,
"slug"
:
"<string>"
,
"title"
:
"<string>"
,
"subtitle"
:
"<string>"
,
"recurrence"
:
"<string>"
,
"image"
:
"<string>"
,
"active"
:
true
,
"createdAt"
:
"<string>"
,
"updatedAt"
:
"<string>"
}
]
}
GET
/
v1
/
series
Try it
Get Series
cURL
curl
--request
GET
\
--url
https://gateway.polymarket.us/v1/series
import requests
url = "https://gateway.polymarket.us/v1/series"
response = requests.get(url)
print(response.text)
const options = {method: 'GET'};
fetch('https://gateway.polymarket.us/v1/series', options)
.then(res => res.json())
.then(res => console.log(res))
.catch(err => console.error(err));
<?php
$curl = curl_init();
curl_setopt_array($curl, [
CURLOPT_URL => "https://gateway.polymarket.us/v1/series",
CURLOPT_RETURNTRANSFER => true,
CURLOPT_ENCODING => "",
CURLOPT_MAXREDIRS => 10,
CURLOPT_TIMEOUT => 30,
CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
CURLOPT_CUSTOMREQUEST => "GET",
]);
$response = curl_exec($curl);
$err = curl_error($curl);
curl_close($curl);
if ($err) {
echo "cURL Error #:" . $err;
} else {
echo $response;
}
package main
import (
"fmt"
"net/http"
"io"
)
func main() {
url := "https://gateway.polymarket.us/v1/series"
req, _ := http.NewRequest("GET", url, nil)
res, _ := http.DefaultClient.Do(req)
defer res.Body.Close()
body, _ := io.ReadAll(res.Body)
fmt.Println(string(body))
}
HttpResponse<String> response = Unirest.get("https://gateway.polymarket.us/v1/series")
.asString();
require 'uri'
require 'net/http'
url = URI("https://gateway.polymarket.us/v1/series")
http = Net::HTTP.new(url.host, url.port)
http.use_ssl = true
request = Net::HTTP::Get.new(url)
response = http.request(request)
puts response.read_body
200
{
"series"
: [
{
"id"
:
"<string>"
,
"slug"
:
"<string>"
,
"title"
:
"<string>"
,
"subtitle"
:
"<string>"
,
"recurrence"
:
"<string>"
,
"image"
:
"<string>"
,
"active"
:
true
,
"createdAt"
:
"<string>"
,
"updatedAt"
:
"<string>"
}
]
}
Query Parameters
​
limit
integer<int32>
Pagination limit
​
offset
integer<int32>
Pagination offset
​
orderBy
string[]
Pagination order
​
orderDirection
string
Pagination order direction
​
slug
string[]
Series slug
​
active
boolean
Whether series is active
​
recurrence
string
Series recurrence pattern
​
params.limit
integer<int32>
​
params.offset
integer<int32>
​
params.orderBy
string[]
​
params.orderDirection
string
​
params.seriesFilters.slug
string[]
​
params.seriesFilters.categoriesIds
integer<int32>[]
​
params.seriesFilters.categoriesLabels
string[]
​
params.seriesFilters.query
string
​
params.seriesFilters.active
boolean
​
params.seriesFilters.recurrence
string
​
params.tagsFilters.includeTemplate
boolean
​
params.tagsFilters.query
string
Response
200
application/json
List of series
Response containing list of series
​
series
object[]
List of series
Show
child attributes
```

### Series API Overview
**Source Routing Target:** https://docs.polymarket.us/api-reference/series/overview

```text
​
Series API
The Series API provides access to series information. Series group related events together (e.g., NFL games, election cycles).
​
Endpoints
Method
Endpoint
Description
GET
/v1/series
Get all series with filtering
GET
/v1/series/id/{id}
Get series by ID
​
Key Series Fields
Field
Description
id
Unique series identifier
slug
URL-friendly identifier
title
Series title
subtitle
Series subtitle
description
Series description
seriesType
Type of series
recurrence
Recurrence pattern (e.g., daily, weekly)
active
Whether series is active
closed
Whether series is closed
archived
Whether series is archived
​
Volume & Liquidity
Field
Description
liquidity
Series liquidity
volume
Total trading volume
volume24hr
24-hour volume
​
Filtering Series
Query series with various filters:
GET
/v1/series?active=
true
&
recurrence
=
daily
&
limit
=
20
​
Common Filters
Parameter
Type
Description
slug
array
Filter by slugs
active
boolean
Filter by active status
closed
boolean
Filter by closed status
archived
boolean
Filter by archived status
recurrence
string
Filter by recurrence pattern
​
Pagination
Parameter
Type
Description
limit
integer
Page size
offset
integer
Page offset
orderBy
array
Fields to order by
orderDirection
string
Order direction (asc/desc)
```

### Get Series By ID (GET)
**Source Routing Target:** https://docs.polymarket.us/api-reference/series/get-by-id

```text
ERROR: Status code 404
```

## Section: Sports
---

### Get League By Slug (GET)
**Source Routing Target:** https://docs.polymarket.us/api-reference/sports/get-league-by-slug

```text
Get League By Slug
cURL
curl
--request
GET
\
--url
https://gateway.polymarket.us/v2/leagues/{slug}
import requests
url = "https://gateway.polymarket.us/v2/leagues/{slug}"
response = requests.get(url)
print(response.text)
const options = {method: 'GET'};
fetch('https://gateway.polymarket.us/v2/leagues/{slug}', options)
.then(res => res.json())
.then(res => console.log(res))
.catch(err => console.error(err));
<?php
$curl = curl_init();
curl_setopt_array($curl, [
CURLOPT_URL => "https://gateway.polymarket.us/v2/leagues/{slug}",
CURLOPT_RETURNTRANSFER => true,
CURLOPT_ENCODING => "",
CURLOPT_MAXREDIRS => 10,
CURLOPT_TIMEOUT => 30,
CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
CURLOPT_CUSTOMREQUEST => "GET",
]);
$response = curl_exec($curl);
$err = curl_error($curl);
curl_close($curl);
if ($err) {
echo "cURL Error #:" . $err;
} else {
echo $response;
}
package main
import (
"fmt"
"net/http"
"io"
)
func main() {
url := "https://gateway.polymarket.us/v2/leagues/{slug}"
req, _ := http.NewRequest("GET", url, nil)
res, _ := http.DefaultClient.Do(req)
defer res.Body.Close()
body, _ := io.ReadAll(res.Body)
fmt.Println(string(body))
}
HttpResponse<String> response = Unirest.get("https://gateway.polymarket.us/v2/leagues/{slug}")
.asString();
require 'uri'
require 'net/http'
url = URI("https://gateway.polymarket.us/v2/leagues/{slug}")
http = Net::HTTP.new(url.host, url.port)
http.use_ssl = true
request = Net::HTTP::Get.new(url)
response = http.request(request)
puts response.read_body
200
{
"league"
: {
"name"
:
"<string>"
,
"slug"
:
"<string>"
,
"image"
:
"<string>"
,
"isOperational"
:
true
,
"id"
:
123
,
"sportId"
:
123
,
"tagId"
:
123
,
"resolution"
:
"<string>"
,
"ordering"
:
"<string>"
,
"activeSeriesId"
:
123
,
"createdAt"
:
"<string>"
,
"abbreviation"
:
"<string>"
}
}
GET
/
v2
/
leagues
/
{slug}
Try it
Get League By Slug
cURL
curl
--request
GET
\
--url
https://gateway.polymarket.us/v2/leagues/{slug}
import requests
url = "https://gateway.polymarket.us/v2/leagues/{slug}"
response = requests.get(url)
print(response.text)
const options = {method: 'GET'};
fetch('https://gateway.polymarket.us/v2/leagues/{slug}', options)
.then(res => res.json())
.then(res => console.log(res))
.catch(err => console.error(err));
<?php
$curl = curl_init();
curl_setopt_array($curl, [
CURLOPT_URL => "https://gateway.polymarket.us/v2/leagues/{slug}",
CURLOPT_RETURNTRANSFER => true,
CURLOPT_ENCODING => "",
CURLOPT_MAXREDIRS => 10,
CURLOPT_TIMEOUT => 30,
CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
CURLOPT_CUSTOMREQUEST => "GET",
]);
$response = curl_exec($curl);
$err = curl_error($curl);
curl_close($curl);
if ($err) {
echo "cURL Error #:" . $err;
} else {
echo $response;
}
package main
import (
"fmt"
"net/http"
"io"
)
func main() {
url := "https://gateway.polymarket.us/v2/leagues/{slug}"
req, _ := http.NewRequest("GET", url, nil)
res, _ := http.DefaultClient.Do(req)
defer res.Body.Close()
body, _ := io.ReadAll(res.Body)
fmt.Println(string(body))
}
HttpResponse<String> response = Unirest.get("https://gateway.polymarket.us/v2/leagues/{slug}")
.asString();
require 'uri'
require 'net/http'
url = URI("https://gateway.polymarket.us/v2/leagues/{slug}")
http = Net::HTTP.new(url.host, url.port)
http.use_ssl = true
request = Net::HTTP::Get.new(url)
response = http.request(request)
puts response.read_body
200
{
"league"
: {
"name"
:
"<string>"
,
"slug"
:
"<string>"
,
"image"
:
"<string>"
,
"isOperational"
:
true
,
"id"
:
123
,
"sportId"
:
123
,
"tagId"
:
123
,
"resolution"
:
"<string>"
,
"ordering"
:
"<string>"
,
"activeSeriesId"
:
123
,
"createdAt"
:
"<string>"
,
"abbreviation"
:
"<string>"
}
}
Path Parameters
​
slug
string
required
League slug
Response
200
application/json
League
​
league
object
Consumer-facing league representation
Show
child attributes
```

### Get Sport By Slug (GET)
**Source Routing Target:** https://docs.polymarket.us/api-reference/sports/get-sport-by-slug

```text
Get Sport By Slug
cURL
curl
--request
GET
\
--url
https://gateway.polymarket.us/v2/sports/{slug}
import requests
url = "https://gateway.polymarket.us/v2/sports/{slug}"
response = requests.get(url)
print(response.text)
const options = {method: 'GET'};
fetch('https://gateway.polymarket.us/v2/sports/{slug}', options)
.then(res => res.json())
.then(res => console.log(res))
.catch(err => console.error(err));
<?php
$curl = curl_init();
curl_setopt_array($curl, [
CURLOPT_URL => "https://gateway.polymarket.us/v2/sports/{slug}",
CURLOPT_RETURNTRANSFER => true,
CURLOPT_ENCODING => "",
CURLOPT_MAXREDIRS => 10,
CURLOPT_TIMEOUT => 30,
CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
CURLOPT_CUSTOMREQUEST => "GET",
]);
$response = curl_exec($curl);
$err = curl_error($curl);
curl_close($curl);
if ($err) {
echo "cURL Error #:" . $err;
} else {
echo $response;
}
package main
import (
"fmt"
"net/http"
"io"
)
func main() {
url := "https://gateway.polymarket.us/v2/sports/{slug}"
req, _ := http.NewRequest("GET", url, nil)
res, _ := http.DefaultClient.Do(req)
defer res.Body.Close()
body, _ := io.ReadAll(res.Body)
fmt.Println(string(body))
}
HttpResponse<String> response = Unirest.get("https://gateway.polymarket.us/v2/sports/{slug}")
.asString();
require 'uri'
require 'net/http'
url = URI("https://gateway.polymarket.us/v2/sports/{slug}")
http = Net::HTTP.new(url.host, url.port)
http.use_ssl = true
request = Net::HTTP::Get.new(url)
response = http.request(request)
puts response.read_body
200
{
"sport"
: {
"name"
:
"<string>"
,
"slug"
:
"<string>"
,
"image"
:
"<string>"
,
"leagues"
: [
{
"name"
:
"<string>"
,
"slug"
:
"<string>"
,
"image"
:
"<string>"
,
"isOperational"
:
true
,
"id"
:
123
,
"sportId"
:
123
,
"tagId"
:
123
,
"resolution"
:
"<string>"
,
"ordering"
:
"<string>"
,
"activeSeriesId"
:
123
,
"createdAt"
:
"<string>"
,
"abbreviation"
:
"<string>"
}
],
"id"
:
123
,
"tagId"
:
123
,
"createdAt"
:
"<string>"
,
"defaultJerseyImage"
:
"<string>"
}
}
GET
/
v2
/
sports
/
{slug}
Try it
Get Sport By Slug
cURL
curl
--request
GET
\
--url
https://gateway.polymarket.us/v2/sports/{slug}
import requests
url = "https://gateway.polymarket.us/v2/sports/{slug}"
response = requests.get(url)
print(response.text)
const options = {method: 'GET'};
fetch('https://gateway.polymarket.us/v2/sports/{slug}', options)
.then(res => res.json())
.then(res => console.log(res))
.catch(err => console.error(err));
<?php
$curl = curl_init();
curl_setopt_array($curl, [
CURLOPT_URL => "https://gateway.polymarket.us/v2/sports/{slug}",
CURLOPT_RETURNTRANSFER => true,
CURLOPT_ENCODING => "",
CURLOPT_MAXREDIRS => 10,
CURLOPT_TIMEOUT => 30,
CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
CURLOPT_CUSTOMREQUEST => "GET",
]);
$response = curl_exec($curl);
$err = curl_error($curl);
curl_close($curl);
if ($err) {
echo "cURL Error #:" . $err;
} else {
echo $response;
}
package main
import (
"fmt"
"net/http"
"io"
)
func main() {
url := "https://gateway.polymarket.us/v2/sports/{slug}"
req, _ := http.NewRequest("GET", url, nil)
res, _ := http.DefaultClient.Do(req)
defer res.Body.Close()
body, _ := io.ReadAll(res.Body)
fmt.Println(string(body))
}
HttpResponse<String> response = Unirest.get("https://gateway.polymarket.us/v2/sports/{slug}")
.asString();
require 'uri'
require 'net/http'
url = URI("https://gateway.polymarket.us/v2/sports/{slug}")
http = Net::HTTP.new(url.host, url.port)
http.use_ssl = true
request = Net::HTTP::Get.new(url)
response = http.request(request)
puts response.read_body
200
{
"sport"
: {
"name"
:
"<string>"
,
"slug"
:
"<string>"
,
"image"
:
"<string>"
,
"leagues"
: [
{
"name"
:
"<string>"
,
"slug"
:
"<string>"
,
"image"
:
"<string>"
,
"isOperational"
:
true
,
"id"
:
123
,
"sportId"
:
123
,
"tagId"
:
123
,
"resolution"
:
"<string>"
,
"ordering"
:
"<string>"
,
"activeSeriesId"
:
123
,
"createdAt"
:
"<string>"
,
"abbreviation"
:
"<string>"
}
],
"id"
:
123
,
"tagId"
:
123
,
"createdAt"
:
"<string>"
,
"defaultJerseyImage"
:
"<string>"
}
}
Path Parameters
​
slug
string
required
Sport slug
Response
200
application/json
Sport with leagues
​
sport
object
Show
child attributes
```

### Sports API Overview
**Source Routing Target:** https://docs.polymarket.us/api-reference/sports/overview

```text
​
Sports API
The Sports API provides access to sporting events organized by league or sport, plus player reference data.
​
Endpoints
Method
Endpoint
Description
GET
/v2/leagues/{slug}/events
Get events by league slug
GET
/v2/sports/{slug}/events
Get events by sport slug
GET
/v1/sports/players
List players or look up players by internal ID, team, or provider ID
​
Players
Use
/v1/sports/players?filters.id=781
to retrieve a specific player directly, or
filters.teamId
to list players on a team. This public endpoint is supported and is not deprecated; there is no standalone v2 players lookup endpoint. See
Players Endpoint
for filters, pagination, response fields, and examples for player props and combos.
​
Get League Events
Retrieve events for a specific league:
GET
/v2/leagues/nfl/events
​
Path Parameters
Parameter
Type
Description
slug
string
League slug (e.g.,
nfl
,
nba
,
mlb
)
​
Query Parameters
Parameter
Type
Description
limit
integer
Pagination limit
offset
integer
Pagination offset
excludeEventId
array
Event IDs to exclude
type
string
Type:
sport
(default) or
futures
section
string
Section:
general
(default) or
trending
​
Get Sport Events
Retrieve events for all leagues under a sport:
GET
/v2/sports/football/events
​
Path Parameters
Parameter
Type
Description
slug
string
Sport slug (e.g.,
football
,
basketball
)
​
Query Parameters
Parameter
Type
Description
limit
integer
Pagination limit
offset
integer
Pagination offset
excludeEventId
array
Event IDs to exclude
type
string
Type:
sport
(default) or
futures
section
string
Section:
general
(default) or
trending
​
Teams
For fetching team information, use the
Sports (Legacy) API
.
```

### Get All Leagues (GET)
**Source Routing Target:** https://docs.polymarket.us/api-reference/sports/get-leagues

```text
ERROR: Status code 404
```

### Get All Sports (GET)
**Source Routing Target:** https://docs.polymarket.us/api-reference/sports/get-sports

```text
Get Sports
cURL
curl --request GET \
--url https://gateway.polymarket.us/v1/sports
import requests
url = "https://gateway.polymarket.us/v1/sports"
response = requests.get(url)
print(response.text)
const options = {method: 'GET'};
fetch('https://gateway.polymarket.us/v1/sports', options)
.then(res => res.json())
.then(res => console.log(res))
.catch(err => console.error(err));
<?php
$curl = curl_init();
curl_setopt_array($curl, [
CURLOPT_URL => "https://gateway.polymarket.us/v1/sports",
CURLOPT_RETURNTRANSFER => true,
CURLOPT_ENCODING => "",
CURLOPT_MAXREDIRS => 10,
CURLOPT_TIMEOUT => 30,
CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
CURLOPT_CUSTOMREQUEST => "GET",
]);
$response = curl_exec($curl);
$err = curl_error($curl);
curl_close($curl);
if ($err) {
echo "cURL Error #:" . $err;
} else {
echo $response;
}
package main
import (
"fmt"
"net/http"
"io"
)
func main() {
url := "https://gateway.polymarket.us/v1/sports"
req, _ := http.NewRequest("GET", url, nil)
res, _ := http.DefaultClient.Do(req)
defer res.Body.Close()
body, _ := io.ReadAll(res.Body)
fmt.Println(string(body))
}
HttpResponse<String> response = Unirest.get("https://gateway.polymarket.us/v1/sports")
.asString();
require 'uri'
require 'net/http'
url = URI("https://gateway.polymarket.us/v1/sports")
http = Net::HTTP.new(url.host, url.port)
http.use_ssl = true
request = Net::HTTP::Get.new(url)
response = http.request(request)
puts response.read_body
200
{
"sports"
: [
{
"sport"
:
"<string>"
,
"image"
:
"<string>"
,
"resolution"
:
"<string>"
,
"ordering"
:
"<string>"
,
"tags"
:
"<string>"
,
"series"
:
"<string>"
,
"isOperational"
:
true
,
"automaticResolution"
:
true
,
"defaultJerseyImage"
:
"<string>"
}
]
}
GET
/
v1
/
sports
Try it
Get Sports
cURL
curl --request GET \
--url https://gateway.polymarket.us/v1/sports
import requests
url = "https://gateway.polymarket.us/v1/sports"
response = requests.get(url)
print(response.text)
const options = {method: 'GET'};
fetch('https://gateway.polymarket.us/v1/sports', options)
.then(res => res.json())
.then(res => console.log(res))
.catch(err => console.error(err));
<?php
$curl = curl_init();
curl_setopt_array($curl, [
CURLOPT_URL => "https://gateway.polymarket.us/v1/sports",
CURLOPT_RETURNTRANSFER => true,
CURLOPT_ENCODING => "",
CURLOPT_MAXREDIRS => 10,
CURLOPT_TIMEOUT => 30,
CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
CURLOPT_CUSTOMREQUEST => "GET",
]);
$response = curl_exec($curl);
$err = curl_error($curl);
curl_close($curl);
if ($err) {
echo "cURL Error #:" . $err;
} else {
echo $response;
}
package main
import (
"fmt"
"net/http"
"io"
)
func main() {
url := "https://gateway.polymarket.us/v1/sports"
req, _ := http.NewRequest("GET", url, nil)
res, _ := http.DefaultClient.Do(req)
defer res.Body.Close()
body, _ := io.ReadAll(res.Body)
fmt.Println(string(body))
}
HttpResponse<String> response = Unirest.get("https://gateway.polymarket.us/v1/sports")
.asString();
require 'uri'
require 'net/http'
url = URI("https://gateway.polymarket.us/v1/sports")
http = Net::HTTP.new(url.host, url.port)
http.use_ssl = true
request = Net::HTTP::Get.new(url)
response = http.request(request)
puts response.read_body
200
{
"sports"
: [
{
"sport"
:
"<string>"
,
"image"
:
"<string>"
,
"resolution"
:
"<string>"
,
"ordering"
:
"<string>"
,
"tags"
:
"<string>"
,
"series"
:
"<string>"
,
"isOperational"
:
true
,
"automaticResolution"
:
true
,
"defaultJerseyImage"
:
"<string>"
}
]
}
Response
200
application/json
Sports details
​
sports
object[]
Show
child attributes
```

### Get Events By League Slug (GET)
**Source Routing Target:** https://docs.polymarket.us/api-reference/sports/get-events-by-league

```text
ERROR: Status code 404
```

### Get Events By Sport Slug (GET)
**Source Routing Target:** https://docs.polymarket.us/api-reference/sports/get-events-by-sport

```text
ERROR: Status code 404
```

## Section: Sports (Legacy)
---

### Sports API Overview (Legacy)
**Source Routing Target:** https://docs.polymarket.us/api-reference/sports-legacy/overview

```text
​
Sports API (Legacy)
The v1 Sports API provides access to sports configuration, player and team information, and sports events. The players lookup remains supported and is not deprecated despite this section’s legacy label; it has no standalone v2 replacement.
​
Endpoints
Method
Endpoint
Description
GET
/v1/sports
Get all sports
GET
/v1/sports/{seriesId}/events
Get events for a series
GET
/v1/sports/teams
Get sports teams
GET
/v1/sports/teams/provider
Get teams by provider
GET
/v1/sports/players
List players or look up players by internal ID, team, or provider ID
​
Get Sports Players
Retrieve player reference data without loading an event. Use
filters.id
for a specific player or
filters.teamId
for players on a team. See
Players Endpoint
for all filters, provider lookup behavior, pagination, response fields, and curl examples.
​
Get Sports
Retrieve available sports and their configuration:
GET
/v1/sports
​
Sport Fields
Field
Type
Description
sport
string
Sport name
image
string
Sport image URL
resolution
string
Resolution configuration
ordering
string
Display ordering
tags
string
Associated tags
series
string
Associated series
isOperational
boolean
Whether sport is operational
automaticResolution
boolean
Whether automatic resolution is enabled
​
Get Sports Events
Retrieve events for a specific series:
GET
/v1/sports/{seriesId}/events
​
Path Parameters
Parameter
Type
Description
seriesId
integer
Series ID
​
Get Sports Teams
Retrieve all sports teams:
GET
/v1/sports/teams
​
Parameters
Parameter
Type
Description
teamIds
array
Filter by team IDs
​
Get Teams by Provider
Retrieve team information from a specific data provider:
GET
/v1/sports/teams/provider?provider=PROVIDER_SPORTRADAR
&
league
=
NFL
​
Parameters
Parameter
Type
Description
teamIds
array
Filter by team IDs
provider
string
Data provider (
PROVIDER_SPORTSDATAIO
or
PROVIDER_SPORTRADAR
)
league
string
League name (e.g., NFL, NBA, MLB)
​
Team Fields
Field
Type
Description
id
integer
Team identifier
name
string
Team name
abbreviation
string
Team abbreviation
displayAbbreviation
string
Display abbreviation
league
string
League name
record
string
Team record
logo
string
Logo URL
alias
string
Team alias
safeName
string
Safe name for URLs
homeIcon
string
Home icon URL
awayIcon
string
Away icon URL
colorPrimary
string
Primary team color
ranking
integer
Team ranking
conference
string
Conference name
providerIds
array
Provider ID mappings
​
Data Providers
Provider
Description
PROVIDER_SPORTSDATAIO
SportsData.io
PROVIDER_SPORTRADAR
Sportradar
```

### Get Sports (GET)
**Source Routing Target:** https://docs.polymarket.us/api-reference/sports-legacy/get-sports

```text
ERROR: Status code 404
```

### Get Sports Teams (GET)
**Source Routing Target:** https://docs.polymarket.us/api-reference/sports-legacy/get-teams

```text
ERROR: Status code 404
```

### Get Sports Events (GET)
**Source Routing Target:** https://docs.polymarket.us/api-reference/sports-legacy/get-events

```text
ERROR: Status code 404
```

### Get Sports Teams For Provider (GET)
**Source Routing Target:** https://docs.polymarket.us/api-reference/sports-legacy/get-teams-provider

```text
ERROR: Status code 404
```

### Get Sports Players (GET)
**Source Routing Target:** https://docs.polymarket.us/api-reference/sports-legacy/get-players

```text
ERROR: Status code 404
```

## Section: Tags
---

### Tags API Overview
**Source Routing Target:** https://docs.polymarket.us/api-reference/tags/overview

```text
​
Tags API
The Tags API provides access to tags used to categorize and organize events and markets. Tags enable filtering and discovery of related content.
​
Endpoints
Method
Endpoint
Description
GET
/v2/tags
Get all tags
GET
/v2/tags/{id}
Get tag by ID
GET
/v2/tags/slug/{slug}
Get tag by slug
GET
/v2/tags/featured
Get featured tags
```

### Get Tags (GET)
**Source Routing Target:** https://docs.polymarket.us/api-reference/tags/get-tags

```text
Get Tags
cURL
curl
--request
GET
\
--url
https://gateway.polymarket.us/v2/tags
import requests
url = "https://gateway.polymarket.us/v2/tags"
response = requests.get(url)
print(response.text)
const options = {method: 'GET'};
fetch('https://gateway.polymarket.us/v2/tags', options)
.then(res => res.json())
.then(res => console.log(res))
.catch(err => console.error(err));
<?php
$curl = curl_init();
curl_setopt_array($curl, [
CURLOPT_URL => "https://gateway.polymarket.us/v2/tags",
CURLOPT_RETURNTRANSFER => true,
CURLOPT_ENCODING => "",
CURLOPT_MAXREDIRS => 10,
CURLOPT_TIMEOUT => 30,
CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
CURLOPT_CUSTOMREQUEST => "GET",
]);
$response = curl_exec($curl);
$err = curl_error($curl);
curl_close($curl);
if ($err) {
echo "cURL Error #:" . $err;
} else {
echo $response;
}
package main
import (
"fmt"
"net/http"
"io"
)
func main() {
url := "https://gateway.polymarket.us/v2/tags"
req, _ := http.NewRequest("GET", url, nil)
res, _ := http.DefaultClient.Do(req)
defer res.Body.Close()
body, _ := io.ReadAll(res.Body)
fmt.Println(string(body))
}
HttpResponse<String> response = Unirest.get("https://gateway.polymarket.us/v2/tags")
.asString();
require 'uri'
require 'net/http'
url = URI("https://gateway.polymarket.us/v2/tags")
http = Net::HTTP.new(url.host, url.port)
http.use_ssl = true
request = Net::HTTP::Get.new(url)
response = http.request(request)
puts response.read_body
200
{
"tags"
: [
{
"id"
:
"<string>"
,
"label"
:
"<string>"
,
"slug"
:
"<string>"
,
"createdAt"
:
"<string>"
,
"updatedAt"
:
"<string>"
,
"image"
:
"<string>"
,
"tradable"
:
true
,
"league"
: {
"id"
:
123
,
"name"
:
"<string>"
,
"sportId"
:
123
,
"tagId"
:
123
,
"image"
:
"<string>"
,
"resolution"
:
"<string>"
,
"ordering"
:
"<string>"
,
"activeSeriesId"
:
123
,
"isOperational"
:
true
,
"automaticResolution"
:
true
,
"createdAt"
:
"<string>"
,
"slug"
:
"<string>"
,
"abbreviation"
:
"<string>"
},
"sport"
: {
"id"
:
123
,
"name"
:
"<string>"
,
"tagId"
:
123
,
"createdAt"
:
"<string>"
,
"slug"
:
"<string>"
,
"image"
:
"<string>"
},
"parentId"
:
123
,
"subtags"
: [
{}
]
}
]
}
GET
/
v2
/
tags
Try it
Get Tags
cURL
curl
--request
GET
\
--url
https://gateway.polymarket.us/v2/tags
import requests
url = "https://gateway.polymarket.us/v2/tags"
response = requests.get(url)
print(response.text)
const options = {method: 'GET'};
fetch('https://gateway.polymarket.us/v2/tags', options)
.then(res => res.json())
.then(res => console.log(res))
.catch(err => console.error(err));
<?php
$curl = curl_init();
curl_setopt_array($curl, [
CURLOPT_URL => "https://gateway.polymarket.us/v2/tags",
CURLOPT_RETURNTRANSFER => true,
CURLOPT_ENCODING => "",
CURLOPT_MAXREDIRS => 10,
CURLOPT_TIMEOUT => 30,
CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
CURLOPT_CUSTOMREQUEST => "GET",
]);
$response = curl_exec($curl);
$err = curl_error($curl);
curl_close($curl);
if ($err) {
echo "cURL Error #:" . $err;
} else {
echo $response;
}
package main
import (
"fmt"
"net/http"
"io"
)
func main() {
url := "https://gateway.polymarket.us/v2/tags"
req, _ := http.NewRequest("GET", url, nil)
res, _ := http.DefaultClient.Do(req)
defer res.Body.Close()
body, _ := io.ReadAll(res.Body)
fmt.Println(string(body))
}
HttpResponse<String> response = Unirest.get("https://gateway.polymarket.us/v2/tags")
.asString();
require 'uri'
require 'net/http'
url = URI("https://gateway.polymarket.us/v2/tags")
http = Net::HTTP.new(url.host, url.port)
http.use_ssl = true
request = Net::HTTP::Get.new(url)
response = http.request(request)
puts response.read_body
200
{
"tags"
: [
{
"id"
:
"<string>"
,
"label"
:
"<string>"
,
"slug"
:
"<string>"
,
"createdAt"
:
"<string>"
,
"updatedAt"
:
"<string>"
,
"image"
:
"<string>"
,
"tradable"
:
true
,
"league"
: {
"id"
:
123
,
"name"
:
"<string>"
,
"sportId"
:
123
,
"tagId"
:
123
,
"image"
:
"<string>"
,
"resolution"
:
"<string>"
,
"ordering"
:
"<string>"
,
"activeSeriesId"
:
123
,
"isOperational"
:
true
,
"automaticResolution"
:
true
,
"createdAt"
:
"<string>"
,
"slug"
:
"<string>"
,
"abbreviation"
:
"<string>"
},
"sport"
: {
"id"
:
123
,
"name"
:
"<string>"
,
"tagId"
:
123
,
"createdAt"
:
"<string>"
,
"slug"
:
"<string>"
,
"image"
:
"<string>"
},
"parentId"
:
123
,
"subtags"
: [
{}
]
}
]
}
Query Parameters
​
limit
integer<int32>
Pagination limit
​
offset
integer<int32>
Pagination offset
​
orderBy
string[]
Pagination order
​
orderDirection
string
Pagination order direction
​
slug
string[]
Tag slug to filter by
​
ids
integer<int32>[]
List of tag IDs to filter by
​
parentId
integer<int32>
Filter by parent tag ID. Ignored if parent_slug is provided.
​
parentSlug
string
Filter by parent tag slug. Takes priority over parent_id if both are provided.
​
query
string
Case-insensitive substring match on tag label.
Response
200
application/json
List of tags
​
tags
object[]
List of tags
Show
child attributes
```

### Get Tag By ID (GET)
**Source Routing Target:** https://docs.polymarket.us/api-reference/tags/get-by-id

```text
ERROR: Status code 404
```

### Get Tag By Slug (GET)
**Source Routing Target:** https://docs.polymarket.us/api-reference/tags/get-by-slug

```text
ERROR: Status code 404
```

### Get Events For A Tag (GET)
**Source Routing Target:** https://docs.polymarket.us/api-reference/tags/get-events

```text
ERROR: Status code 404
```

## Section: Search
---

### Search API Overview
**Source Routing Target:** https://docs.polymarket.us/api-reference/search/overview

```text
​
Search API
The Search API allows you to search for events and markets by query string.
​
Endpoints
Method
Endpoint
Description
GET
/v1/search
Search for events and markets
​
Search
Find events and markets matching a query:
GET
/v1/search?query=super+bowl
&
limit
=
10
​
Query Parameters
Parameter
Type
Description
query
string
Search query
limit
integer
Maximum number of results to return
page
integer
Page number for pagination
seriesIds
array
Filter by series IDs
marketType
array
Filter by market types
status
string
Filter by status
startTimeMin
string
Minimum start time filter
startTimeMax
string
Maximum start time filter
closedTimeMin
string
Minimum closed time filter
closedTimeMax
string
Maximum closed time filter
​
Response
Returns matching events with their associated markets:
{
"events"
: [
{
"id"
:
"123"
,
"slug"
:
"super-bowl-winner"
,
"title"
:
"Super Bowl Winner"
,
"category"
:
"sports"
,
"active"
:
true
,
"markets"
: [
...
]
}
]
}
```

### Search (GET)
**Source Routing Target:** https://docs.polymarket.us/api-reference/search/get-search

```text
ERROR: Status code 404
```

## Section: Incentives
---

### Incentives API Overview
**Source Routing Target:** https://docs.polymarket.us/api-reference/incentives/overview

```text
​
Incentives API
The Incentives API exposes the active incentive programs and the rewards you have earned. For background on how programs work and their reward formulas, see the
Incentive Programs overview
; for how liquidity programs score — Target Size, Discount Factor, and Max Spread — see the
Liquidity Incentive Program
page.
​
Base URL
https://api.polymarket.us
Field casing.
Query parameters are
snake_case
(e.g.
page_size
). Response bodies are
lowerCamelCase
(e.g.
marketSlug
). Sending a camelCase query parameter (e.g.
pageSize
) is silently ignored and the default is used.
​
Endpoints
Method
Endpoint
Auth
Description
GET
/v1/incentives
Required
Get incentive programs
GET
/v1/incentives/earnings
Required
Get your incentive earnings
Authentication
Both endpoints require API key authentication — see the
Authentication guide
.
​
Get Incentive Programs
Returns active and historical incentive programs grouped by market.
GET
/v1/incentives?page_size=
10
&
symbols
=
aec-nba-bos-nyk-2026-04-01
​
Query Parameters
Parameter
Type
Required
Description
page_size
integer
No
Number of markets per page. Use with
page_token
for pagination.
page_token
string
No
Pagination token from a previous response’s
nextPageToken
.
symbols
string[]
No
Filter by market symbols.
order_by
string
No
Sort field. Defaults to
created_at
.
order_direction
string
No
Sort direction:
asc
or
desc
. Defaults to
desc
.
statuses
string[]
No
Filter by status:
active
,
closed
, or
pending
.
program_type
string
No
Filter by program type, such as
liquidityProgram
or
volumeProgram
.
query
string
No
Case-insensitive substring match on market slug.
instrument_states
string[]
No
Filter by instrument lifecycle state.
category
string
No
Filter by exact event category.
subcategory
string
No
Filter by exact event subcategory.
​
Response
{
"programs"
: [
{
"marketSlug"
:
"aec-nba-bos-nyk-2026-04-01"
,
"instrumentState"
:
"INSTRUMENT_STATE_OPEN"
,
"category"
:
"sports"
,
"subcategory"
:
"basketball"
,
"eventStartTime"
:
"2026-04-01T23:30:00Z"
,
"instrumentProduct"
:
"moneyline"
,
"timePeriods"
: [
{
"programId"
:
"nba_t1_ml_early"
,
"programType"
:
"liquidityProgram"
,
"start"
:
"2026-03-28T04:00:00Z"
,
"end"
:
"2026-04-01T21:00:00Z"
,
"rewardPool"
:
3000.0
,
"status"
:
"closed"
,
"discountFactor"
:
0.40
,
"targetSize"
:
20000
,
"period"
:
"early"
,
"createdAt"
:
"2026-03-28T01:00:00Z"
,
"maxSpread"
:
0.035
},
{
"programId"
:
"nba_t1_ml_day_of"
,
"programType"
:
"volumeProgram"
,
"start"
:
"2026-04-01T21:00:00Z"
,
"rewardPool"
:
3000.0
,
"status"
:
"active"
,
"minTakerNotional"
:
100
,
"period"
:
"day_of"
,
"createdAt"
:
"2026-03-28T01:00:00Z"
}
]
}
],
"nextPageToken"
:
"abc123"
}
Ongoing programs omit
end
until an end time is set.
​
IncentiveProgram Fields
Field
Type
Description
marketSlug
string
Market identifier
timePeriods
TimePeriod[]
Incentive periods for this market
instrumentState
string
Exchange lifecycle state of the instrument
category
string
Event category from instrument metadata
subcategory
string
Event subcategory from instrument metadata
eventStartTime
string
Event start time from instrument metadata
instrumentProduct
string
Product from instrument metadata
​
TimePeriod Fields
Field
Type
Description
programId
string
Unique program period identifier
programType
string
Program type (e.g.
liquidityProgram
)
start
string
ISO 8601 start timestamp
end
string
ISO 8601 end timestamp (optional; omitted for ongoing programs)
rewardPool
number
Total reward pool for this period in USD
status
string
active
,
closed
, or
pending
discountFactor
number
Discount factor for scoring (optional; omitted if unset)
targetSize
integer
Liquidity programs: minimum aggregate resting size, in contracts, on a side of the book for that side to qualify (optional; omitted if unset)
maxSpread
number
Liquidity programs only. Optional
half-width
in price dollars (
0.035
= 3.5¢ from mid, so a 7¢ gap). Where set, a second pays only if both sides of the book reach
targetSize
with each size-adjusted price within
maxSpread
of the midpoint. Omitted (never
0
) when the program has no Max Spread. See the note below
period
string
Reward period type:
early
,
day_of
,
live
, etc.
createdAt
string
ISO 8601 timestamp when the program was created
minTakerNotional
integer
Minimum taker notional for volume programs (optional)
Reading
maxSpread
.
A liquidity program may carry a maximum spread from the midpoint. Where it does:
Units.
maxSpread
is in price dollars of a $1 contract (
0.035
= 3.5¢). The docs pages and polymarket.us/rewards quote the same value in cents; the API always returns dollars. It is a
half-width
: the two sides may be up to 2 ×
maxSpread
apart (3.5¢ from the midpoint = a 7¢ gap).
What is compared.
Once per sampled second, each side of the book is walked from its best price outward, one whole price level at a time, until the resting size on that side (all participants combined) reaches
targetSize
. The price level that gets there is that side’s
size-adjusted price
. The midpoint is halfway between the two size-adjusted prices — not the best-bid/best-offer midpoint. A small order at the best price counts toward that side’s depth like any other order; it moves the size-adjusted price only when it is what carries the side to
targetSize
.
Pass / fail.
This is a test of the book, not of each trader: you do not have to quote both sides yourself. The second is scored as usual (every order from the best price through the size-adjusted price qualifies, weighted by its distance from that side’s best price and by its size) when both sides reach
targetSize
and each size-adjusted price is no more than
maxSpread
from the midpoint — a gap of exactly 2 ×
maxSpread
passes. If either side never reaches
targetSize
, or the gap is wider than 2 ×
maxSpread
,
nobody is paid for that second
, including makers quoting tightly and including a side that did reach
targetSize
. Once a second qualifies, a one-sided quote still earns on the side it rests on. A failed second still counts toward the period’s total, so its share of
rewardPool
is forfeited, not shifted to other seconds or other makers.
Tick size.
The check is in dollars, so a given
maxSpread
means the same thing on 1¢-tick and 0.1¢-tick markets.
Omission.
The key is absent (never
0
) when a program has no Max Spread; it is a
liquidityProgram
field. Programs without a Max Spread score each side independently, as before.
Scope.
The value applies to every scored second of that
timePeriods[]
entry. Parameters can differ between time periods of the same market, so read
maxSpread
per entry rather than per market.
Full explanation and worked example:
What is Max Spread?
.
​
Get Incentive Earnings
Returns rewards earned by the authenticated caller. Each entry sums all payouts for a single
(market, date)
pair, where
date
is in Eastern Time.
GET
/v1/incentives/earnings?start_date=2026-03-21
&
market_slug
=
aec-nba-bos-nyk-2026-04-01
​
Query Parameters
Parameter
Type
Required
Description
start_date
string
No
Start date filter (
YYYY-MM-DD
). Defaults to program launch.
end_date
string
No
End date filter (
YYYY-MM-DD
). Omit for through-today.
market_slug
string
No
Filter by market slug.
program_type
string
No
Filter by program type (e.g.
liquidityProgram
).
​
Response
{
"rewards"
: [
{
"reward"
:
1828.62
,
"programType"
:
"liquidityProgram"
,
"marketSlug"
:
"tsc-nba-ny-okc-2026-03-29-223pt5"
,
"date"
:
"2026-03-30"
,
"status"
:
"PAID"
},
{
"reward"
:
325.97
,
"programType"
:
"liquidityProgram"
,
"marketSlug"
:
"aec-cbb-cabap-kan-2026-03-20"
,
"date"
:
"2026-03-29"
,
"status"
:
"PENDING"
}
]
}
Each daily entry represents rewards earned from midnight-to-midnight ET. Callers with no rewards receive
{"rewards":[]}
.
​
UserReward Fields
Field
Type
Description
reward
number
Reward amount in USD (sum of all payouts for this market on this date)
programType
string
Program type (e.g.
liquidityProgram
)
marketSlug
string
Market identifier
date
string
Reward date in Eastern Time (
YYYY-MM-DD
)
status
string
Payout disposition:
PAID
,
PENDING
, or
SKIPPED
​
Rate Limits
Endpoint
Rate Limit
GET /v1/incentives
5 requests / second
GET /v1/incentives/earnings
5 requests / second
```

### Get Incentive Programs (GET)
**Source Routing Target:** https://docs.polymarket.us/api-reference/incentives/get-programs

```text
ERROR: Status code 404
```

### Get Your Incentive Earnings (GET)
**Source Routing Target:** https://docs.polymarket.us/api-reference/incentives/get-earnings

```text
ERROR: Status code 404
```

