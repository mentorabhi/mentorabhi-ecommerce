# S1-M05 — Checkout, orders and simulated payment

Revision 2 · 2026-10-24 · Design reviewed; implementation may begin.

Design: [checkout and recovery contract](design.md). Editable diagram: [checkout-saga.mmd](checkout-saga.mmd). Review: [design review](design-review.md). Decision: [ADR 0005](../../decisions/0005-persisted-checkout-saga.md). Original proposal: [S1-M05 Excalidraw](../../../architecture/stage-1/S1-M05.excalidraw).

Manual end-user checks: [manual acceptance](manual-acceptance.md). Verification evidence will be added after implementation.

## Scope

Convert the customer's saved cart into a reproducible quote and order using current Catalog, Pricing, Inventory and Customer service contracts. Reserve stock, hold eligible coupon capacity, authorize/capture a local simulated payment, confirm the order and schedule local simulated fulfillment. Persist each workflow transition so restarts and retries resume safely.

## Reviewed design decisions

- Orders owns immutable checkout snapshots, idempotency records, the order lifecycle and durable Saga progress.
- Inventory remains authoritative for stock reservations; Pricing remains authoritative for coupon holds and redemption.
- Payment simulation owns payment operation records. Fulfillment simulation owns shipment scheduling records.
- The Saga is orchestrated by the Orders service and persisted in its PostgreSQL database. Each external step uses a stable operation key. A PostgreSQL worker claims due steps with row locks and can resume after process restart.
- Catalog, Configuration, Inventory, Pricing, Payment and Fulfillment internal routes use the checkout-only service identity. The admin UI exposes versioned checkout simulation settings.
- Kafka and event consumers remain S1-M06. M05 writes transactional outbox records but does not claim Kafka delivery.
- No real payment provider, tax authority, carrier, cloud service or hosted model is used.

Review confirmed the requirements, service-owned state, money/quote snapshots, final-unit and coupon concurrency, idempotency, payment reconciliation, compensation, narrow service identity, restart fencing, and local resource measurement gates. Findings and changes are in the review record. No blocking design issue remains; implementation has not started.
