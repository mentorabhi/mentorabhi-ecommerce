# S1-M10 design review

Revision 1 · 2026-10-24 · Review completed before implementation.

## Findings and decisions

- **Identity and privacy:** use a reserved demo username prefix, `.invalid` email domain, generated Indian address values, and local-only random credentials in ignored mode-0600 files. Do not send email or store real user contact data.
- **Service ownership:** create catalog/pricing/inventory/customer state through each owner API. Orders owns its fixture import and outbox rows. The generator coordinates APIs and never queries another service's private tables.
- **Event contract:** use the existing version-1 `OrderAccepted` and `OrderConfirmed` event shapes. Validate the full envelope and payload before a transaction; carry the generated date in `occurredAt` and outbox `created_at` so Order History and the lakehouse use consistent time.
- **Idempotency:** stable `(seed, customer index, order index)` source references guard import retries. The same SKU, user and inventory idempotency keys must be reused on replay. Conflicting source-reference content returns a conflict.
- **Money:** compute line subtotals and tax/shipping in integer minor units; reject overflow and inconsistent total arithmetic. Do not create a fake refund or external payment. Report currency-specific amounts only.
- **Stock:** generate order lines first, aggregate item demand by SKU, then add stock plus a safety buffer using inventory adjustments before importing orders. Inventory remains nonnegative.
- **Scale, revision 2:** honor the original 1–100 total items per customer, partitioned into 1–5 items/order. The prior weighted order-count interpretation is superseded. Stream batches of at most 100 orders; do not materialize every event in memory.
- **Analytics correctness:** M08 reports group order metrics by accepted/confirmed event time. Validate counts and totals against the same source-reference set and currency before claiming dashboard success.
- **Failure handling:** stable idempotency permits retry after a partial run. Preserve the returned seed manifest and do not offer a reset/delete option in the first increment.

## Review outcome

Design is ready to implement with the route opt-in by default and an explicit local configuration switch. Automated tests must cover disabled access, operator/customer authorization, malformed batch rejection, atomicity, idempotent retry, event contract, and generated count bounds. Runtime and dashboard reconciliation remain unverified until the seed is imported and M08 analytics is running.

Revision 2 review: enablement is temporary through `devops/scripts/seed-demo`; a privileged realm role plus reserved identity protects the import boundary. Stock adjustments record historical supply and historical sales separately, retaining the safety buffer. Catalog allows relative SVG/JPEG/PNG/WebP keys, rejecting remote URLs and traversal. Product images represent a model; size/edition variants share its photo. Per-user generator unit coverage checks total items, line count, date bounds, money and stable replay for 1,000 users.

UI scale review: fetching two HTTP snapshots for every SKU makes the 106-SKU storefront burst exceed M09's ingress budget. Add bounded public read batches (maximum 100 UUIDs) to the existing Pricing and Inventory snapshot boundaries; the storefront loads 100 IDs per batch, retaining the same price/stock response fields and validating currency consistency. Four snapshot requests replace 212 for the expanded catalog. No price, reservation, stock or checkout authority moves into the UI.
