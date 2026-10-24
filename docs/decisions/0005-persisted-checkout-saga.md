# ADR 0005 — Persisted checkout Saga and scoped service identity

Date: 2026-10-24 · Status: accepted for S1-M05 implementation after design review.

## Context

Checkout crosses Orders, Pricing, Inventory, Payment Simulator and Fulfillment Simulator, cannot share a database transaction, and must survive duplicate requests, process restarts, uncertain payment responses and partial compensation. ADR 0003 removes operator role distinctions, so internal machine authorization must not reuse the broad operator API audience. The baseline Mac has 16 GB RAM and Docker is currently allocated 7.75 GiB.

## Decision

1. Orders owns the immutable order snapshot, customer-scoped idempotency records, durable Saga steps and order outbox. It coordinates the workflow through a persisted PostgreSQL worker using row locking, lease renewal and monotonic fencing tokens. Claim `(customer_subject, idempotency_key)` and canonical payload hash before mutable reads; a matching accepted retry returns its original order without a new quote/address read. Changed payload conflicts only within the same customer scope; another customer's same key is independent.
2. Each downstream operation uses a stable order/step idempotency identity and canonical payload hash. Downstream services reject stale fence values, return the result of identical completed operations, and conflict on changed payload reuse. This is at-least-once orchestration with deterministic idempotent effects; it is not described as exactly-once delivery.
3. Catalog returns authoritative active SKU, product and category facts through its internal checkout contract. Orders passes these Catalog facts to Pricing, avoiding a service dependency cycle. Pricing owns one consistent quote plus coupon hold/protect/commit/release and redemption limits; holds bind to quote revisions. Inventory owns atomic stock reserve/protect/commit/release operations. Their service-local transactions are authoritative.
4. Payment and Fulfillment are local simulator services with their own operation records. Payment status is reconciled before retrying, compensating or releasing resources. Fulfillment schedules only after order confirmation and retries independently.
5. Checkout authentication uses the customer-realm token for customer-owned order actions and synchronous Customer address retrieval. Orders snapshots the validated address before asynchronous work and never persists or forwards the customer bearer token.
6. Orders obtains downstream credentials from a dedicated Keycloak client service account. Internal `/api/v1/internal/checkout/**` routes require the exact operator-realm issuer, `supersports-checkout-internal-api` audience, `azp=supersports-checkout-worker`, operation scope and current fence. Existing admin routes continue to require `supersports-api`; tokens cannot cross route families. The checkout credential is only available to Orders.
7. Payment capture follows authorization and protected stock/coupon holds. Inventory allocation and Pricing redemption commit in their respective services before Orders marks the order `CONFIRMED`. Partial finalization remains `MANUAL_REVIEW`; no service writes another service's tables. The confirmation and `OrderConfirmed` outbox row share an Orders DB transaction.
8. Configuration owns revisioned local tax/shipping/reservation/simulator inputs, with an operator-editable categorized UI. Each order snapshots the active revision and exact calculation inputs.
9. M05 persists outbox records but does not publish to Kafka. Kafka/CDC/projections remain M06.
10. Use local deterministic tax/shipping/payment/fulfillment simulations; no real provider, cloud service or hosted model is used.

## Alternatives

- Temporal: defer until measurements or workflow visibility/scale requirements justify its additional local services. Current official docs support PostgreSQL persistence; see the [Temporal persistence docs](https://docs.temporal.io/temporal-service/persistence) and [maintained local Compose sample](https://github.com/temporalio/samples-server/blob/main/compose/docker-compose-postgres.yml).
- Synchronous request-thread orchestration: rejected because restart loses control flow and a client timeout obscures the outcome.
- Cross-service database transaction: rejected because each service owns its database and external simulated effects cannot join it.
- Reuse `supersports-api` for the worker: rejected because it is the broad operator audience under ADR 0003.

## Consequences and verification

The order worker and downstream services need durable fencing/idempotency schemas, internal route authorization tests and independent failure-injection tests. Protected inventory/coupon capacity may remain held during manual review; the operator must resolve payment and owning-service state through audited idempotent actions. Full Docker startup, concurrent checkout and peak memory must be measured before declaring 16 GB acceptance. Existing M03/M04 APIs remain the owners for pricing, inventory, catalog and customer data. The local order/address snapshot is retained until the owner resets the learning dataset; this is not a production retention policy.
