# CDC restart probe design review

Revision 1 · 2026-10-24

## Review lenses

- **Data integrity:** the only write is a standard idempotent checkout. Orders remains authoritative during broker downtime. No outbox, slot, topic, or consumer offset is reset. The test compares stable event IDs and aggregate sequence through the serving History projection.
- **Recovery and cleanup:** service startup belongs in `finally`; health and connector/task readiness are bounded. The accepted order is retained as synthetic integration evidence, as with other checkout journeys.
- **Scope accuracy:** this proves one broker and connector restart with retained WAL and current local offsets. It cannot prove multi-broker durability or consistent snapshot/WAL overlap.
- **Test reliability:** use the repository's serialized streaming integration runner, generated idempotency key, dynamic SKU and customer token; no fixed event offsets or assumed order totals.

## Disposition

No design blocker. Implementation must make restoration unconditional and assert the full order lifecycle and all event IDs, not just connector health. The test result will be recorded separately from this proposal. Independent review is unavailable in the current session; this owner review records the concrete safety and evidence criteria.
