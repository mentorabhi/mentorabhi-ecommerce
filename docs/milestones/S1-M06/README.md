# S1-M06 — Outbox, Kafka and CQRS projections

Revision 7 · 2026-10-24 · CDC, owner-scoped projection, consumer crash injection and audited poison replay implemented. Automated/runtime evidence is in [verification](verification.md). Manual acceptance remains open.

Design: [outbox and projection design](design.md). Review: [design review](design-review.md). Decision: [ADR 0006](../../decisions/0006-orders-outbox-cdc-and-history-projection.md). Editable flow: [event-flow.mmd](event-flow.mmd). Manual checks: [manual acceptance](manual-acceptance.md). Source architecture: [S1-M06 diagram](../../../architecture/stage-1/S1-M06.excalidraw).

## Objective

Publish committed order events from the Orders transactional outbox to local Kafka, then consume them into an independently owned customer order-history projection. Demonstrate at-least-once delivery, deduplication, bounded ordering, restart recovery, dead-letter handling and full projection rebuild.

## Guardrails

- PostgreSQL remains authoritative for orders. Kafka and CQRS projections are derived and rebuildable.
- No service reads another service's private database. The order-history service owns its database and reads its events from Kafka.
- Event replay and duplicate delivery are expected. Consumers deduplicate by stable event ID.
- Do not claim exactly-once delivery. State the tested recovery boundary and freshness lag.
- Keep Kafka optional in the lightweight local profile; provide a complete streaming profile and document memory use on the 16 GB baseline.
- No cloud services or hosted messaging/schema services.

Implemented scope delivers transactional outbox enrichment/backfill, Debezium CDC, local Kafka, durable consumer inbox and per-order projection, customer-scoped reads, a one-shot crash after projection commit/before offset commit, and operator-authenticated poison correction/replay with immutable audit and resumable publication intent. New canonical hashes allow semantically identical object formatting and numeric representation to deduplicate while retaining legacy raw fingerprint evidence. Consumer validation now enforces the versioned event envelope and payload fields, including privacy restrictions. See [operator workflow detail](operator-workflows.md). Isolated projection rebuild/reconciliation/cutover remains pending; the full design objective is not complete.
