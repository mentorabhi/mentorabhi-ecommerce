# S1-M10 — Synthetic commerce dataset for analytics

Revision 2 · 2026-10-24 · Design reviewed before implementation; item-count clarification recorded below.

## Goal

Populate the local SuperSports storefront and analytics stack with reproducible, visibly synthetic Indian customer profiles, 100 inventory SKUs, and one year of order history. This gives the user realistic catalog photography and enough time-series volume to inspect Admin → Analytics without cloud services or real transactions.

## Dataset contract

- Create 10 parent products (six cricket, four football), each with 10 sellable size/color/grade variations. A variation is one SKU and one inventory balance, for exactly 100 SKUs.
- Create 1,000 customer identities and owner-service profiles. Names and Indian addresses are generated data; usernames use a reserved `ss-demo-*` prefix and email uses `.invalid`. No mail is sent. Store generated login credentials only in ignored `devops/.local/` files with mode 0600.
- Give every customer 1–100 items in total, uniformly selected, split into orders of 1–5 items. This corrects the first design's interpretation of the user's requested item count as an order count. Choose order dates uniformly in the preceding 364 days, with a five-minute margin before generation time.
- Give each order 1–5 distinct SKU lines, quantity one per line. Select INR by default with a small USD share to exercise the currency-separated reports. Use current active catalog prices and configured tax/shipping values.
- Generate 10 photorealistic product images. Size/color variations of one model share that model's image and have distinct SKU attributes and prices.
- Use a fixed seed by default and an explicit `--seed` override. Stable source references and API idempotency keys make retries safe. Report actual users, orders, lines, order-date bounds, currencies, and SKUs created.

## Data ownership and event history

Catalog, pricing, inventory, identity, and customer data are written through their owning local APIs. Orders own order, line, and outbox data. A narrowly scoped local synthetic-order import boundary will validate and persist bounded batches in the Orders service, including accepted/confirmed event envelopes with the requested event time. It will not make cross-service database reads or represent a payment provider, shipment, or refund as a real operation. The existing local payment simulator remains the only payment implementation.

The order fixture is a synthetic reporting/history record. Its source reference is stable and unique; the API rejects conflicting reuse. M08 analytics consumes the same Orders outbox event contract as ordinary local orders. Event timestamps use generated order dates; dataset metadata records generation time and seed separately.

## Scale and resource bounds

- Expected volume is about 17,000 orders and 50,000 items for 1,000 profiles, bounded by 100,000 items/orders.
- Import in bounded batches of at most 100 orders and use four profile-creation workers. Support a smaller `--users`/`--max-items` rehearsal before the full run. Persist generation time, settings, and credentials before writing external state so retries reproduce the payload.
- Derive stock adjustments from generated quantities. Add historical supply plus a buffer of max(50, 10% of demand), then subtract historical sales through Inventory's audited adjustment API, with stable keys for both movements. The resulting available stock is the buffer. Repeating the same run does not change it.
- The data is persistent and has no destructive cleanup by default. A seed report identifies all source references for a later reviewed cleanup operation.

## Acceptance

- Re-running the same seed produces no duplicate identities, products, SKUs, inventory movements, orders, or outbox events.
- Every imported event passes the existing Order History contract and every order belongs to one generated customer.
- `catalog` returns 10 new product models and 100 active SKUs; Inventory reports 100 nonnegative balances.
- Customer and Orders APIs return the generated profiles and owner-scoped order history.
- Admin → Analytics can filter the generated year by INR/USD and shows nonzero order count, GMV, daily trend, and top products. Trino totals reconcile against Orders outbox accepted events for the same time window/currency.
- No real payment, external email, or fulfillment is performed.

## Open implementation review items

1. Route is disabled by default. The local operation temporarily enables it; only the reserved seeder identity with a non-default Keycloak realm role explicitly assigned using bootstrap admin can import. A self-registered matching username has no import authority. Disable the route when the operation exits.
2. Validate the existing versioned event envelope fields and value bounds before inserting any batch.
3. Make a batch atomic and stable under retry. Reject partial SKU references, invalid currencies, out-of-window dates, negative money, mismatched line totals, and duplicate source references.
4. Bound generated dataset size and memory; stream batches rather than holding all event payloads.
5. Validate 16 GB feasibility with the actual local Compose profile and retain an analytics-only rehearsal option.
