# M07 event compatibility design review

Revision 1 · 2026-10-24

## Findings and decisions

- **V1 contract drift:** V1 stays unchanged; new event types and version value live in a separate JSON Schema.
- **Unsafe caller-controlled versions:** Orders selects V2 through an allowlisted event-writing method rather than a request field.
- **Projection regression:** both versions share inbox/event identity and sequence checks; V2 state transitions are explicit and rebuild uses the same parser.
- **Sensitive payload spread:** V2 payload allowlists exclude address, free text, bearer token, raw subject and payment instrument. Product text is not carried in post-purchase events.
- **Rollout ordering:** dual-version History support is built before Units 3/4 emit V2, so a committed business event cannot be poisoned by an older consumer.

## Disposition

No design blocker. Implementation must preserve V1 fixtures and migration history unchanged, keep V2 schemas authoritative for all V2 fields, and teach reconciliation both versions. Source changes and test code may be authored now; execution is deferred until Stage 1 development is complete.
