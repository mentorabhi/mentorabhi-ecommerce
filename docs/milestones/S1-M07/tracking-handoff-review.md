# M07 Unit 2 design review

Revision 1 · 2026-10-24

## Review lenses

- **Ownership:** Fulfillment owns shipment facts and audit; Orders owns customer/order ownership and its read model. Cross-service access stays on APIs with service identity.
- **Race safety:** handoff and future cancellation must contend on one locked shipment row and revision. The operator must provide an expected revision; a stale action cannot silently advance state.
- **Retry safety:** a stable operation UUID and immutable request fingerprint return an original receipt for exact replay and conflict on changed target/reason.
- **Compatibility:** no new event is sent to the v1 History consumer in this unit. Unit 8 first introduces the v2 contract and dual-version consumer, then enables lifecycle mirroring.
- **Product meaning:** statuses and ETA are labeled simulated; delivered state is the simulator's explicit transition, not a scheduled estimate.

## Disposition

No design blocker. A later implementation review must verify operator JWT audience/subject, shipment-row locking, immutable transition audit, customer ownership before the Fulfillment lookup, and migration restart behavior. Browser controls are intentionally deferred to Unit 8. Test code is authored now; execution is deferred until the requested development-first pass across Stage 1.
