# M07 Unit 8 design review

Revision 1 · 2026-10-24

- **Authority:** Orders verifies customer ownership before asking Fulfillment for tracking. Operator transitions are applied only by Fulfillment under an operator token and expected revision.
- **Lifecycle compatibility:** immutable v1 events remain unchanged. v2 cancellation/refund events are written by Orders after final state commits and exclude sensitive address/customer text.
- **Review safety:** product-facing content is only `PUBLISHED`; moderation actions retain operator identity and reason.
- **Support privacy:** tickets/messages remain in the Support database and do not enter Kafka. Customer access predicates include the verified JWT subject.
- **Restock correctness:** Inventory alone inspects unit conditions and writes stock movements for SELLABLE units. The refund decision is not coupled to restock.
- **Tracking event choice:** the current authoritative query is adequate for customer tracking; do not synthesize CDC events from another service's private database. A durable owner-side mirror would need its own design and is outside this UI integration slice.
- **Decision:** ready for the shipment simulator UI and route integration. New verification remains deferred until all Stage 1 development is complete.
