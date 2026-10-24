# S1-M05 design — Checkout Saga and compensation

Revision 2 · 2026-10-24 · Reviewed; implementation in progress.

## Goal and boundary

Make the M04 cart purchasable through local, deterministic simulations. Checkout must create one immutable order snapshot for one customer and one currency, reserve stock atomically, consume coupon capacity safely, simulate payment, confirm the order, and schedule simulated fulfillment. Retrying a request or restarting a worker must not create duplicate effects.

This milestone delivers checkout and order creation only. Order tracking, customer cancellation, return/refund requests, reviews and support remain S1-M07. Kafka publication and CQRS projections remain S1-M06. The cart is not the transactional authority and may change after the checkout snapshot is created.

## Requirements and acceptance mapping

| Requirement | S1-M05 behavior |
|---|---|
| R04 / AE03 | Read active currency and explicit currency price book at quote time. Store integer minor units and currency on every line and total. Existing orders keep their original values when the store currency changes. |
| R06 / AE05–AE08 | Idempotent checkout, authoritative stock reservation, deterministic simulated payment, durable workflow state, compensation, timeout recovery and visible manual resolution. |
| R07 / AE09 | Pricing owns coupon eligibility and capacity. Checkout obtains an atomic hold before authorization, commits it on confirmation, or releases it on failure. |
| R10 / AE12 | Tax, shipping, reservation timeout and simulator behavior are explicit versioned local configuration inputs. No live tax/carrier integration. |
| R14 | PostgreSQL remains transactional authority. Order outbox rows are committed atomically with state changes; M06 owns Kafka/CDC and projections. |
| R16–R17 | Unit, contract, integration, concurrency, failure-injection, restart, browser and manual DB checks are required before the M05 checkpoint. |

## Service and data ownership

| Component | Owns | Checkout contract |
|---|---|---|
| Storefront | Checkout form and status display only | Sends SKU IDs, quantities, optional coupon code and idempotency key. It cannot send prices, discount, tax, shipping, owner subject or authoritative address contents. |
| Orders | Order header/lines, quote snapshot, idempotency key/payload hash, Saga state/steps, operation references and transactional outbox | Authenticates the customer realm. Derives owner only from verified `sub`. Exposes only that customer's orders. |
| Catalog | Active product/SKU and category state | An authenticated internal checkout lookup returns active SKU plus Catalog-sourced product/category identity and product title. No private-table reads; Pricing never trusts browser-provided category data. |
| Pricing | Active currency, per-SKU prices, coupon definitions and usage holds | One quote operation returns currency, all line prices, coupon allocation, rounding result and revision token from a consistent database snapshot. Coupon hold is bound to that quote and can be protected, committed or released idempotently. |
| Inventory | On-hand ledger and reservations | Atomically reserves all requested lines or none. Competing requests for the final unit cannot both succeed. Protect, commit-to-allocation and release are idempotent operations by order key. |
| Customer | Profile/address and customer identity boundary | The authenticated checkout request retrieves the current Indian address and snapshots it before queuing asynchronous work. Never persist or forward the customer's bearer token. Customer tokens are never accepted by M03 operator APIs. |
| Configuration | Versioned checkout simulation settings | Stores and validates active tax, shipping, reservation timeout and payment-simulation settings. Operators manage them in the categorized Configuration area; each activation increments revision and records actor. Orders snapshots one active revision for each checkout calculation. |
| Payment Simulator | Authorization, capture, void and refund operation ledger | Deterministic local responses; every mutation accepts an idempotency key and rejects a changed payload for a reused key. Status lookup by operation identity reconciles ambiguous responses. No card number or bank data is collected. |
| Fulfillment Simulator | Simulated shipment request, state and local tracking identifier | Schedule after order confirmation. Retrying the same order returns the original shipment. No carrier API is used. |

Services communicate over documented APIs. The checkout worker uses a dedicated Keycloak service-account client `supersports-checkout-worker` and `supersports-checkout-internal-api` audience, without the broad operator `supersports-api` audience. Internal routes live under `/api/v1/internal/checkout/**`; they require the exact operator-realm issuer, the internal audience, and `azp=supersports-checkout-worker`. Route-level security matchers in Catalog, Configuration, Inventory, Pricing, Payment and Fulfillment separate these routes from operator endpoints, which continue to require `supersports-api`. Internal routes reject customer-only, operator-only, wrong-issuer and wrong-client tokens; operator routes reject internal-only tokens. An internal token can invoke only the checkout client's documented route set. The incoming customer token is used synchronously for the customer-owned Order API and Customer profile retrieval only; it is not persisted or forwarded to the worker. Public product/price reads are not treated as checkout authority; checkout revalidates active SKU, currency, price, coupon eligibility and stock with owning services.

## Quote and snapshot rules

1. Require an authenticated customer token from the `supersports-customers` realm and an `Idempotency-Key` of bounded length/character set. Normalize the payload and compute its canonical hash.
2. Before any mutable Catalog, Pricing, Configuration or Customer reads, atomically insert a `VALIDATING` checkout-request claim unique on `(customer_subject, idempotency_key)` with payload hash and a short validation lease. A matching concurrent request returns the same owner-scoped request state; a changed hash conflicts. Another customer may independently use the same key without learning whether the first customer's key exists.
3. Normalize line items by SKU: quantities are positive integers, duplicate SKU lines are combined with overflow checks, and the service enforces the configured per-order/per-line limits.
4. For each SKU, call Catalog's internal checkout lookup. It returns the authoritative active flag, product ID, category ID/slug, title and Catalog revision. Orders supplies these Catalog-sourced facts—not browser category claims—to Pricing's quote operation. This avoids a Pricing→Catalog call cycle; Pricing trusts facts only from the authenticated checkout service client.
5. Request one authoritative Pricing quote. It returns active currency, every current line price, coupon eligibility/discount allocation, rounding result and monotonic quote/revision identifiers atomically. Reject mixed currency, inactive/missing SKU, unavailable price and any invalid coupon with a stable user-safe error before reservation. The coupon hold later must bind to this quote and its revisions; if any changed, return a requote conflict without side effects.
6. Read the active checkout simulation configuration revision and calculate tax/shipping using the versioned local values. Snapshot the revision and exact inputs.
7. Fetch the current Customer profile/address synchronously during this authenticated request. Require the valid Indian country/state/PIN fields already enforced by Customer. Copy the validated address into the order snapshot before queuing work, so the restartable worker never needs a customer token and later profile edits do not rewrite history.
8. In one Orders transaction, persist the idempotency result, immutable order snapshot and durable Saga row; change request status from `VALIDATING` to `ACCEPTED`. The customer token is discarded. Only this transaction enqueues side effects. A matching retry after acceptance returns the original order/status without repeating mutable reads. A deterministic validation rejection is stored and replayed for the same key; after changing price/coupon/cart terms, the customer starts a new attempt with a new idempotency key. If the validation lease expires after a process crash, a retry with the same owner/key/hash and fresh customer token may resume validation; no stock/payment side effect has occurred yet.

Money uses signed 64-bit integer minor units and a three-letter currency code. Percent coupon values are basis points (10000 = 100%); arithmetic uses checked operations and a documented rounding mode. An idempotency retry with the same customer/key/hash returns the original order and current status. The same owner's key with a different payload returns conflict and causes no side effect.

Demo coupon math uses half-up rounding to the nearest minor unit. Apply the coupon only to eligible lines, capped at their subtotal. Allocate a multi-line discount proportionally using integer division, then distribute remaining minor units by largest fractional remainder with SKU UUID as a stable tie-breaker; allocated line discounts must sum exactly to the order discount. Demo tax defaults to 1800 basis points on merchandise subtotal after coupon and excludes simulated shipping; tax is rounded half-up once per order. Shipping defaults are explicit per-currency demo values (INR 9900 minor units, USD 199 minor units) with no exchange-rate conversion. Keep these values versioned in the categorized Configuration service and label them as simulations; they are not tax or shipping compliance advice. The order stores the settings revision and exact formula inputs.

## Durable checkout workflow

After synchronous authentication, quote and address snapshot, Orders creates a `PENDING` order and durable workflow row in one database transaction. The customer token is discarded after the request. A worker claims due workflow work using `FOR UPDATE SKIP LOCKED`, records attempt/lease metadata, and performs one remote operation at a time. Each claim increments a monotonically increasing fencing token. Every transition update compares the token and expected prior state; a stale worker cannot advance or compensate a newer attempt. The token is also sent on internal service calls. Each downstream service stores the highest accepted token per order plus stable operation key and canonical payload hash; stale tokens are rejected, and an identical completed operation returns its original result. A reused operation key with a changed payload conflicts. Leases are renewed while work is active; startup/periodic polling reclaims only expired leases. The worker is bounded and poll interval/retry backoff are configurable; no retry is described as exactly-once delivery.

Forward steps:

1. Revalidate Catalog state and atomically bind/validate the Pricing quote revisions before any resource is reserved.
2. Reserve all inventory lines atomically, with an expiry and order-scoped idempotency key.
3. Place coupon usage hold atomically if a coupon was used.
4. Authorize simulated payment for the snapshotted total/currency.
5. Before capture, confirm both holds are still active and extend them to protected status. Protected holds are not automatically expired while payment outcome is ambiguous; if bounded protection is exhausted, retain the holds and move to manual review rather than making units/coupon capacity available behind a possible capture.
6. Capture the authorized simulated payment with the same stable operation identity. The payment ledger exposes operation status by order-and-step identity; reconcile status before retrying a dependent step, voiding, refunding or releasing holds.
7. Commit the Inventory reservation to a consumed allocation and commit the coupon hold as a redemption by calling each owning service's idempotent internal API. If a worker crashes after capture, reconcile payment by operation key, then retry those owning-service commits. Do not confirm the order until both are committed. If an owning service cannot commit after the bounded retry/review threshold, mark `MANUAL_REVIEW`, preserve protected stock/coupon state and captured-payment reference, and require explicit audited resolution.
8. In one Orders database transaction, transition to `CONFIRMED` and append `OrderConfirmed` to the transactional outbox.
9. Ask Fulfillment Simulator to schedule the confirmed order. A scheduling failure retries independently and leaves the order confirmed with fulfillment visibly pending; it does not undo a paid order.

Compensations before confirmation run in reverse order: refund a captured payment or void an authorization, release coupon hold, then release stock. Each compensation is durable, retried and idempotent. Do not claim that distributed compensation is an atomic rollback. If the outcome of an operation is ambiguous, query/retry the same operation key and reconcile before advancing or compensating. If a compensation cannot complete within its bounded retry policy, transition the order to an explicit `MANUAL_REVIEW` state with failed step, last safe error code and operator-visible recovery action. Never hide a captured payment or reserved unit behind a generic failure.

Reservation and coupon holds have expiries long enough for bounded retries. Expiry is stored and enforced by the owning service. Before capture, the worker extends/protects both holds. Protected holds remain unavailable until the order reaches a reconciled terminal state or an operator resolves `MANUAL_REVIEW`; they must never expire automatically while capture outcome is unknown. A worker waking after an ordinary expired hold must revalidate/reacquire before capture. Exact default TTL, protection window, retry budget and backoff are implementation configuration, recorded with measured local behavior before acceptance.

Inventory reservation states are `HELD` → `PROTECTED` → `COMMITTED`, with `RELEASED`/`EXPIRED` terminal alternatives. `available = on_hand - HELD - PROTECTED`; commit appends an order-sourced negative stock movement and reduces on-hand once. Pricing coupon-hold states are `HELD` → `PROTECTED` → `COMMITTED`, with `RELEASED`/`EXPIRED` alternatives; both HELD and PROTECTED count against global and per-customer limits. State changes and ledger entries are in the owning service's database transaction and keyed by order plus operation identity. If a cross-service finalization partially succeeds, the workflow remains `MANUAL_REVIEW`; an operator resolves the captured payment, committed inventory and coupon redemption through audited idempotent compensation commands. A committed order can never rely on an expiring reservation.

## Lifecycle and API shape

Order states: `PENDING` → `CONFIRMED` → `FULFILLMENT_PENDING`/`FULFILLMENT_SCHEDULED`; failures before confirmation become `FAILED` after successful compensation or `MANUAL_REVIEW` while unresolved. Payment and fulfillment have their own independently owned states. State transitions are validated in deterministic domain code and stored with revision/audit timestamps.

Initial public API proposal:

- `POST /api/v1/orders/checkout` — customer token, idempotency header, item list and optional coupon code; returns `202` with order ID/state, or a deterministic validation/conflict response.
- `GET /api/v1/orders/checkout-requests/{requestId}` — owner-scoped validation/replay status for concurrent or retried requests; another subject receives `404`.
- `GET /api/v1/orders/{id}` — returns only an order owned by token `sub` (404 for missing or another customer's order).
- `GET /api/v1/orders` — paginated orders scoped to token `sub`.

Internal APIs are versioned and documented in OpenAPI. They use a dedicated local service identity, accept order-scoped idempotency keys, never accept an owner identifier from the browser, and do not expose payment credentials. Orders stores the validated destination snapshot in its service-owned database, avoids logging address/phone fields, and returns the snapshot only through the owning customer's order API and the authenticated local operator workspace. The local learning profile retains the order/address snapshot until the owner resets the local dataset; this is not a production retention policy. Admin/manual-resolution endpoints require the existing authenticated local operator flow and append actor/reason audit records.

Proposed internal route groups are `/api/v1/internal/checkout/catalog/skus/{id}` (active SKU and category facts), `/api/v1/internal/checkout/configuration` (read active revision), `/api/v1/internal/checkout/inventory/reservations` (reserve/protect/commit/release), `/api/v1/internal/checkout/pricing/quote` and `/coupon-holds` (hold/protect/commit/release), `/api/v1/internal/checkout/payments` (authorize/capture/status/void/refund), and `/api/v1/internal/checkout/fulfillment` (schedule/status/cancel). Each route checks the smallest required scope (`checkout:catalog.read`, `checkout:configuration.read`, `checkout:inventory.*`, `checkout:pricing.*`, `checkout:payment.*`, `checkout:fulfillment.*`) in addition to exact issuer, `aud`, `azp` and fence. Keycloak grants these scopes only to the checkout worker client; the worker credential is available only to Orders. Negative tests must prove the checkout client cannot use operator routes and other clients cannot use these internal routes.

## Local technology and resource proposal

Use the existing pinned Spring Boot/JDK/PostgreSQL conventions. Persist workflow progress in the Orders database, avoiding a Temporal cluster and its additional runtime services for this learning-sized milestone. Keep service boundaries for Orders, Payment Simulator and Fulfillment Simulator; add Inventory/Pricing reservation APIs. Dockerize all new workloads under the existing devops Compose profile. Use an optional lightweight `checkout` profile only if measured startup/memory results require it; preserve one full integration profile.

Temporal remains an alternative for a later scale/reliability exercise. Current [official Temporal persistence documentation](https://docs.temporal.io/temporal-service/persistence) supports PostgreSQL persistence for self-hosted services, while the maintained [local PostgreSQL Compose sample](https://github.com/temporalio/samples-server/blob/main/compose/docker-compose-postgres.yml) includes a Temporal server and administration tooling in addition to the application. That additional moving infrastructure is not justified before measuring the database-backed implementation on the 16 GB baseline. Reconsider only if workflow visibility, scheduling, scale or operational requirements exceed the local worker design.

## Failure and concurrency acceptance

- Two customer checkouts compete for the last unit: exactly one reservation and confirmation succeed; inventory never becomes negative.
- Same customer/key/same payload is replayed and returns the original order; key reuse with changed lines/coupon conflicts without another reservation or payment.
- A coupon's final global or per-customer redemption is raced: one hold succeeds. Failed checkout releases the hold; confirmed order commits it once.
- Authorization decline releases stock and coupon holds; no order is confirmed and no capture occurs.
- Capture response is lost: retry/query by payment operation key reconciles the existing result without duplicate capture; do not release stock until the outcome is known.
- Worker is killed between every pair of steps: restart resumes from persisted state and never skips a required validation or duplicates an effect.
- Worker lease expires during a delayed call: higher-fence worker resumes; lower-fence worker cannot mutate downstream state or persist stale Saga progress.
- Reservation/coupon expires before capture: no payment is captured against an expired hold; compensation and final state are explicit.
- Capture succeeds but Inventory/Pricing commit is unavailable: order remains unconfirmed with protected holds; restart/retry commits each owning service by operation key before confirmation.
- Refund/void, coupon release or stock release failure: order reaches `MANUAL_REVIEW`, preserves the outstanding action, and exposes a safe local operator resolution path.
- Fulfillment outage after confirmation: order remains confirmed, schedule retries idempotently, and no payment refund is incorrectly triggered.
- Currency changes after checkout: order retains original amount/currency and address snapshot.
- Customer A cannot list/read B's order; customer token cannot access Catalog/Pricing/Inventory/Configuration operator routes; operator token cannot read Customer data. Verify direct APIs and post-restart behavior.
- Operator-only, customer-only, wrong-client and stale-fence tokens are rejected by each internal route; checkout-worker token cannot call operator routes.

## Alternatives

| Alternative | Decision |
|---|---|
| Temporal self-hosted workflow | Defer: robust durable workflow product, but extra containers and operational surface are premature for the single local checkout flow. Reassess with actual workflow telemetry. |
| Synchronous request thread as the Saga | Reject: process restart loses in-flight control flow and client timeout makes outcome ambiguous. |
| Database transaction spanning service schemas | Reject: violates service-owned databases and cannot atomically include simulator side effects. |
| Storefront calculates authoritative order totals | Reject: browser state is mutable and prices/stock can change after browsing. |
| Globally unique customer idempotency key | Reject: another customer could squat on a key and cause a denial or expose whether it exists. Scope it to customer subject. |
| Real payment/carrier/tax providers | Out of scope: local deterministic simulation only. |

## Review gate and implementation exit

Before code changes, review this design and the editable diagram for payment ambiguity, transaction ownership, service authentication, coupon/stock races, address ownership, retry recovery, data privacy and 16 GB feasibility. Resolve critical findings in the design/ADR first.

After implementation, the milestone requires: unit tests for arithmetic/state rules; contract tests for public and internal APIs; integration tests with real PostgreSQL and all local services; concurrency tests for final stock/coupon limits; restart/outage/failure injection at each Saga boundary; browser E2E for quote/checkout/order status; Selenium coverage for responsive UI and operator recovery; documented manual end-user checks for services, UI journeys and owned DB state; plus actual memory/startup measurements. Keep M06 outbox-to-Kafka claims clearly marked future until exercised.
