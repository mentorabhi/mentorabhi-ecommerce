# S1-M06 — Outbox, Kafka and CQRS projections

Revision 11 · 2026-10-25 · Automated local acceptance includes retained-history reconciliation, rebuild/cutover, snapshot/WAL overlap, actual state/outbox rollback, the concurrent burst, 15-minute paced checkout soak and 15-minute inactive-slot/idle-consumer recovery. Full streaming regression previously passed 6/6; focused additional probes passed separately. Owner manual sign-off remains pending. Exact windows, offered rate and resource limits are in the [completion matrix](acceptance-matrix.md) and [verification record](verification.md).

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

Implemented scope delivers transactional outbox enrichment/backfill, Debezium CDC, local Kafka, durable inbox and per-order projection, customer-scoped reads, a one-shot commit/offset crash, and operator-authenticated poison replay with immutable audit and resumable publication intent. Canonical hashes deduplicate equivalent formatting/numbers while retaining legacy evidence; consumer validation enforces versioned envelope/payload fields and privacy restrictions. Reconciliation emits one JSON fact per row to stay within the local PostgreSQL memory cap; the optional streaming profile gives Order History a 768 MiB container cap (512 MiB Java heap).

`stream-reconcile` compares retained source/Kafka/inbox facts, timeline, current order state/ownership/lines/money and replay provenance. `stream-rebuild` uses a separate database/group, two captured high-water marks, preserved audits, candidate reconciliation and readiness-checked cutover. Dry runs and injected mismatches preserve the active target. Full integration verified recovery and continued new-order delivery after cutover. See [operator workflow detail](operator-workflows.md), [implementation review](rebuild-review.md), and [verification](verification.md). The latest soak/retention and rollback designs add reproducible measured acceptance; owner manual results remain separate.
