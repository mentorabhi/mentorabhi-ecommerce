# M07 Unit 4 design review

2026-10-24 · Owner review before source changes

## Review findings and resolutions

1. Current Catalog values cannot define a refund for an old order. The design allocates from immutable captured line totals and tax snapshot.
2. Rounding each partial request independently can exceed tax or make retry totals vary. The design allocates tax once at order level, distributes integer remainders by stable SKU order, then reserves unique unit ordinals under the Orders order lock.
3. Concurrent requests can claim the last unit twice. Locking the customer order and line slots in one transaction serializes the claim; the database uniqueness constraint is the durable backstop.
4. Return request is not inspection or restock. Orders never changes Inventory stock in this unit; Unit 5 owns received condition and restock movements.
5. Orders cannot infer delivery from its last locally emitted checkout event. Fulfillment's authenticated internal status remains authoritative until Unit 8 adds event mirroring; an unavailable status fails closed.
6. Payment and Orders cannot share a database transaction. Stable Payment operation identity and exact amount make the remote effect safely replayable; unresolved conflicts remain visible rather than issuing a second refund.

## Review outcome

No blocker found. Proceed with the separate return-claim schema and customer API, using v2 event types already allowlisted. Keep operational status distinct from inspection status and do not claim that a return is physically received. Author test and manual-check sources, but defer execution until all Stage 1 development is complete.
