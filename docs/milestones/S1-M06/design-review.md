# S1-M06 design review

Revision 1 · 2026-10-24 · Two independent review passes; findings resolved in design revision 2 and manual checklist revision 2.

## Review roles and result

Two local session reviewers examined the design, editable flow and manual checklist against S1-M05, accepted requirements R14/R16/R17, service ownership, local-only and 16 GB ARM64 constraints. No external model CLIs were used.

The first pass found gaps in legacy event identity/sequence, snapshot/WAL overlap, consumer/DLQ crash ordering, aggregate gap handling, replay audit, projection rebuild cutover and historical reconciliation. The second pass found missing per-order sequence seeding, stale flow diagram, insufficient memory/profile bounds, unclear customer ownership and retention, and manual steps that were not executable.

## Resolutions

| Finding | Resolution |
|---|---|
| Existing M05 rows lack event UUID, version, sequence and customer ownership key. | Additive deterministic backfill; UUIDv5 from existing outbox ID; sequence by per-order row order; HMAC customer key; enrich accepted snapshot only from immutable order/line facts; quarantine orphans; assert quarantine is empty. |
| New events might reuse sequence values after migration. | Migration seeds each sequence row to the per-order maximum backfilled sequence; next event is required to use max+1. |
| Snapshot/WAL overlap and connector publish-before-offset crash can duplicate events. | Consistent snapshot-to-WAL handoff; acceptance injects overlapping writes/restarts; consumers dedupe stable event ID and canonical payload hash. |
| Consumer DB commit and Kafka offset commit are separate. | Projection/inbox commit first then offset; inbox makes redelivery a no-op. DLQ write and poison offset commit share a Kafka transaction. |
| Sequence gaps could stall a whole partition or silently skip order state. | Persist per-order gap buffer, park only that aggregate, continue other orders, drain when predecessor arrives; timed gap remains visibly blocked pending reconciliation. |
| Replay could duplicate or rewrite applied history. | Operator CLI requires stable operation ID and correction payload; append-only actor/reason/source/hash audit; same event ID with changed applied hash conflicts. |
| Rebuild cutover could miss events or destroy the active projection. | Build isolated candidate from earliest, catch up to successive per-partition high-water marks, reconcile, then atomic switch; failure retains old target. Historical limits are explicit. |
| Customer subject and event retention were underspecified. | Use local HMAC ownership key, exclude raw subject and sensitive details, derive API owner only from verified token, reject caller owner filters; document local access and retention limitations. |
| Streaming resource feasibility was vague. | Specify separate core and streaming profiles, 2.25 GiB proposed streaming container limits under 2.5 GiB cap and current 7.75 GiB Docker allocation; actual ARM64/peak/throughput measurements remain acceptance gates. |
| Manual tests lacked direct commands/expected outcomes. | Manual checklist now gives profile/status, UI, REST isolation, broker/connector/consumer recovery, DLQ correction/replay, rebuild fault injection and read-only SQL steps. Final names are to be aligned with implementation migrations and CLI. |

## Review disposition

The reviewer focused on outbox/CDC and ordering confirmed the revised design and diagram have no blockers after the sequence seed and diagram corrections. The resource/ownership reviewer confirmed the profile and privacy design resolves their blockers. That reviewer identified three manual procedure gaps; explicit consumer crash, Connect restart, correction-file/stable-operation-ID replay and rebuild-failure commands were added. The final manual checklist was then checked against the command contract by the implementation owner; a further independent receipt for that last checklist-only edit is not available because the session's agent concurrency limit was reached. The checklist remains subject to implementation-driven command/table-name alignment.

Design is approved for implementation with no architectural blocker. Runtime feasibility, image version/ARM64/license verification, exact M06 CLI behavior and manual execution are not claimed complete by this document.
