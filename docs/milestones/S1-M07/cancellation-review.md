# M07 Unit 3 cancellation design review

Revision 1 · 2026-10-24

## Review lenses

- **Eligibility race:** the Orders order row establishes checkout completion; Fulfillment's shipment row lock arbitrates the final cancellation claim against handoff.
- **Money:** refund uses the immutable captured order total and currency. Payment independently caps cumulative refunds. Zero-value captures skip an invalid zero refund operation.
- **Inventory:** cancellation uses a new idempotent positive stock movement on Inventory's committed reservation, distinct from return inspection/restock.
- **Retries:** Orders records step outcomes and stable derived operation IDs before advancing. A timeout retries the same key; an ambiguous terminal conflict enters visible manual review.
- **Event safety:** only after all authoritative simulator outcomes does an Orders transaction mark CANCELLED and append an allowlisted v2 event. V1 remains unchanged.
- **Privacy:** customer subjects remain inside Orders. No token, address or free-form reason is forwarded to dependent services or Kafka.

## Disposition

No architectural blocker. Implementation must preserve the cancellation claim before refund/stock effects, test the concurrent handoff boundary, and make each downstream effect independently idempotent. Manual review must retain actor, reason and resolved step. Verification is deferred until the user's Stage 1 development-first pass is complete.
