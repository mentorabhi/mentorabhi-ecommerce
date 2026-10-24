# ADR 0006 — Orders outbox CDC and local order-history projection

Date: 2026-10-24 · Status: accepted for S1-M06 implementation after design review.

## Context

M05 writes order lifecycle events transactionally with Orders state. M06 must make those events available to independent consumers and provide customer order history without coupling query reads to the Orders write database. Local operation on the 16 GB ARM64 baseline, replayability, explicit delivery semantics and service-owned persistence are required.

## Decision

1. Use Debezium Kafka Connect to stream committed Orders outbox inserts from PostgreSQL logical WAL into a local Apache Kafka KRaft cluster. Do not poll/update `published_at` to signal publication.
2. Add a versioned immutable envelope with stable event UUID, per-order monotonic sequence, occurred time, event type/version, aggregate ID, pseudonymous ownership key and data. Migrate existing rows deterministically before connector activation; seed sequence state to each aggregate's backfilled maximum.
3. Kafka delivery is at least once. Kafka Connect offsets/internal topics are persistent; consumers use an inbox and canonical payload hashes. No exactly-once end-to-end claim.
4. Build Order History as a separate service and database consuming events only. It derives the owner key from the validated customer token and rejects caller-supplied owner filters.
5. Use repository JSON Schema contracts and CI compatibility tests for the initial event set. Defer a schema registry until independent producer/version needs justify another local dependency.
6. Support partition-keyed ordering per order, durable sequence-gap buffering, transactional poison-event DLQ/offset handling, operator-audited idempotent replay, reconciliation and isolated projection rebuild/cutover.
7. Run Kafka, Connect and Order History through an explicit local streaming profile. Default core remains available independently. Measure ARM64 support, resource use, startup, lag and throughput before accepting the proposed memory limits.
8. Events and projection data contain synthetic, minimized data only. Raw customer subject/address/email/payment details are excluded; ownership uses a local HMAC key. Retention and reset remain explicit local learning-profile operations, not a production policy.

## Alternatives

- Application polling publisher: rejected for this milestone because it introduces a lease/published-state coordination path and polling load; WAL CDC captures committed inserts and fits the existing outbox ownership.
- Direct service-to-service history reads: rejected because it couples read availability to Orders and does not demonstrate CQRS or independent projection rebuild.
- Hosted Kafka/Schema Registry: rejected by the local-only requirement.
- Event sourcing: rejected; Orders PostgreSQL remains transactional authority and events are integration records, not the source of truth.
- Exactly-once claims: rejected; database transactions, Kafka offsets and external projections have separate failure boundaries. Stable identities and idempotency provide tested at-least-once recovery.

## Consequences and verification

Orders needs logical replication configuration and additive migration/backfill. Kafka and Connect require persistent local volumes and WAL/lag/disk monitoring. Order History needs independent authorization, inbox/gap/replay schemas, and rebuild operations. Acceptance requires crash tests at source publication, projection commit/offset commit and DLQ boundaries; legacy snapshot overlap and next-sequence checks; customer/operator isolation; DLQ correction/replay; failed and successful rebuild cutovers; exact dependency pin/license/ARM64 verification; and measured resource evidence. Full manual checks are separate in `docs/milestones/S1-M06/manual-acceptance.md`.
