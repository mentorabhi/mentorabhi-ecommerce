# S1-M06 — Outbox, Kafka and CQRS projections

Revision 8 · 2026-10-24 · Adds isolated projection rebuild, reconciliation and readiness-checked cutover; full CI passed. Remaining design acceptance is tracked in the [completion matrix](acceptance-matrix.md).

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

Implemented scope delivers transactional outbox enrichment/backfill, Debezium CDC, local Kafka, durable inbox and per-order projection, customer-scoped reads, a one-shot commit/offset crash, and operator-authenticated poison replay with immutable audit and resumable publication intent. Canonical hashes deduplicate equivalent formatting/numbers while retaining legacy evidence; consumer validation enforces versioned envelope/payload fields and privacy restrictions.

`stream-reconcile` compares retained source/Kafka/inbox facts, timeline, current order state/ownership/lines/money and replay provenance. `stream-rebuild` uses a separate database/group, two captured high-water marks, preserved audits, candidate reconciliation and readiness-checked cutover. Dry runs and injected mismatches preserve the active target. Full CI verifies recovery and continued new-order delivery after cutover. See [operator workflow detail](operator-workflows.md) and [implementation review](rebuild-review.md). Broader source/DLQ crash probes, explicit ordering/freshness scenarios, sustained load and owner manual results remain open; the full design objective is not yet complete.
