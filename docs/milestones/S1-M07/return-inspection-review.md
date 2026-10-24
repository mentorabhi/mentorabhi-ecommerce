# M07 Unit 5 design review

2026-10-24 · Owner review before source changes

## Review findings and resolutions

1. **Cross-database reads would violate ownership.** Orders sends an authenticated unit manifest after refund confirmation; Inventory persists its own receipt rows and never queries Orders tables.
2. **Orders may stop after recording a refund.** A separate persisted registration flag and worker lease retry the idempotent Inventory manifest until the receipt is confirmed.
3. **Partial manifests can create untracked stock.** Registration and inspection are atomic per return; inspection must cover exactly every received unit and match the current revision.
4. **Duplicate inspection can add stock twice.** The operation audit, unit terminal states, stable movement keys and stock update share one Inventory transaction; unique constraints backstop the movement ledger.
5. **A damaged item must not erase a valid refund.** Inspection decisions control restock only; refund remains a completed Orders/Payment fact.
6. **Operator reason text is untrusted.** It is length-bounded, escaped by the UI, stored only in Inventory audit, and never emitted into commerce events.

## Review outcome

The design is ready for implementation. Use the worker's existing narrow service identity and the Inventory operator audience; do not add a new service or cross-service database access. Test source and manual instructions are required, but execution remains deferred.
