# Checkout burst probe design review

Revision 1 · 2026-10-25 · Reviewed before implementation

- **Bounded impact:** Defaults are 20 checkouts, eight workers and a hard maximum of 50 orders/16 workers. Each checkout is one unit of an existing synthetic football SKU, with unique idempotency keys.
- **No real-world side effect:** Only local simulated payment and fulfillment APIs are used. A keyed Inventory adjustment may add synthetic safety stock; its movement key is included in the ignored result file.
- **Correctness oracle:** HTTP acceptance alone is insufficient. The test verifies each unique order reaches the expected terminal checkout/shipment state, owner-scoped reads return it, stock is nonnegative, and the streaming group catches up.
- **Resource evidence:** Sample memory during execution rather than infer it from idle `docker stats`; record Docker allocation, image versions, worker count and actual sample interval. A finite burst is not called sustained capacity.
- **Privacy and repeatability:** Store IDs, latencies, memory and counts in a mode-restricted ignored `.local` report; do not store access tokens, passwords, addresses, or names.

No design blocker identified. The implementation must fail closed if APIs, stock, or the streaming profile are unhealthy, and must preserve the result report even when an assertion fails after orders have been accepted.
