# S1-M06 design — Outbox, Kafka and CQRS projections

Revision 2 · 2026-10-24 · Design review findings resolved; final review pending.

## Objective and acceptance

Make committed order lifecycle events available to independent local consumers and build a customer-owned order-history read model. Orders PostgreSQL remains authoritative. The projection is derived and rebuildable from retained Kafka events.

1. Each order transition and event record commit atomically.
2. Events carry a stable UUID, event type/version, aggregate ID/sequence, timestamp and validated JSON payload. Kafka key is the order ID; consumers enforce per-order sequence independently of partition order.
3. PostgreSQL logical CDC publishes committed outbox inserts to local Kafka. Connector and broker restarts resume from durable offsets without silent event loss in tested crash scenarios.
4. Consumer inbox deduplicates events and prevents stale/gapped state from silently regressing or advancing the projection.
5. Poison events enter a named DLQ with source topic/partition/offset and error code. Operator replay is audited, idempotent and cannot rewrite an already applied event.
6. A separate order-history service/database serves customer-scoped reads. The owner filter comes only from the verified customer token; caller-supplied subject/customer filters are rejected. UI shows freshness and stale/unavailable state.
7. Rebuild uses a new projection target, records per-partition Kafka high-water marks, catches up to a second mark, reconciles, then atomically changes the active target. On failure, the old target remains active.
8. Tests cover contract compatibility, atomic outbox writes, snapshot/WAL overlap, duplicate/delayed events, consumer and connector crashes, DLQ/replay, ownership isolation, deterministic rebuild and reconciliation.

## Scope boundaries

Stream Orders lifecycle events already created by M05: accepted, confirmed, fulfillment scheduled, payment declined and checkout expired. This does not introduce event sourcing or change commerce authority. Product search remains later (M08); graph and lakehouse projections are S1-M08. No hosted schema service is required: JSON Schema contracts live in `contracts/`, compatibility is checked in CI, and contract versions are immutable. Revisit a local schema registry only if independent producers make repository validation insufficient.

## Components and ownership

| Component | Responsibility and data owner |
|---|---|
| Orders | Authoritative order state and versioned outbox. Inserts event in the same transaction as the state transition. |
| Orders PostgreSQL | Logical WAL stream; slot lag and WAL retention are monitored. |
| Debezium Kafka Connect | Reads the Orders WAL and routes outbox inserts to Kafka. Connector config/offsets are durable local state. |
| Kafka | Local KRaft broker, versioned order topic and DLQ. Single-node replication factor one is for development and is not HA. Order ID is record key. |
| Order History | Independent consumer/query service with its own database, inbox, gap buffer, replay audit and projection. Never queries Orders' private database. |
| Storefront | Reads the customer-scoped projection API; command and checkout routes remain on Orders. |
| Devops | Owns streaming profile, connector config, health/lag/DLQ monitoring, replay/rebuild/reconciliation scripts under `devops/`. |

## Event contract and legacy migration

Envelope fields: `eventId` (UUID), `eventType`, `eventVersion`, `aggregateType`, `aggregateId`, `aggregateSequence`, `occurredAt`, `customerKey`, and `data`. Per-order sequence allocation uses an Orders-owned sequence row locked and incremented in the same transaction as the order update/outbox insert. New event IDs are generated in that transaction. Canonical payload hashes are verified through CDC, inbox, DLQ and replay.

Do not place raw customer subjects, email, addresses, identity tokens, payment instrument data, or secrets in event payloads. `customerKey` is HMAC-SHA256 of the Keycloak subject with a generated local key shared only by Orders event creation and Order History API authorization. The HTTP owner filter is derived from the validated token, never from a caller-provided owner. Kafka, Connect, DLQ and projection stores are internal local services with no host-public ports; access is limited to service identities and local operators. Data is synthetic; this learning profile retains events until explicit reset, exposes disk usage, and does not claim a production retention policy.

M05's current outbox has `bigserial id`, `aggregate_id`, `event_type`, `payload`, `created_at`, and an unused `published_at`. An additive migration adds `event_id`, `event_version`, `aggregate_sequence` and `customer_key`, retaining `id` as CDC primary key and keeping `published_at` for compatibility. Existing rows are backfilled in ascending `id` per aggregate. IDs are deterministic UUIDv5 values from a fixed repository namespace and legacy row ID; sequence is row order. Ownership HMAC is derived from the related order. Legacy `OrderAccepted` events are enriched from immutable order header/lines without address details. Other historical payloads remain limited to recorded fields; no missing historical facts are invented. Rows without a related order enter an explicit migration quarantine and must be zero before connector activation. Re-running migration validation must produce the same IDs, sequences and payload hashes. The migration seeds each per-order sequence row to the maximum backfilled sequence; the first post-migration event must receive exactly max+1.

The connector starts only after migration/backfill. Debezium takes a consistent initial snapshot then follows WAL from its recorded LSN. Snapshot/WAL overlap and publish-before-source-offset crashes can redeliver; inbox uniqueness and canonical hash make duplicate publication a no-op. Acceptance creates an outbox row during a snapshot/restart window and compares unique event ID/hash sets from Orders outbox, Kafka and projection inbox. Connector tests cover restart before and after publish. Never update `published_at` as a substitute for CDC offsets or delete source rows based on publication.

## Delivery, ordering, DLQ and replay

Delivery is at least once from WAL through Connect and Kafka. Connect internal topics and offsets use persistent local volumes. For a valid event, the consumer commits projection plus inbox and payload hash in one database transaction, then commits its Kafka offset. A crash after the database commit but before offset commit redelivers; inbox dedupes. A retryable database failure rolls back and leaves the offset uncommitted.

For invalid/poison events, the consumer uses a Kafka transaction to write the original record plus source coordinates/error code to the DLQ and commit the consumed offset. Crash before transaction commit retries; after commit both DLQ record and offset are durable. DLQ record key is source topic/partition/offset (or deterministic coordinate-derived quarantine ID for malformed envelopes). Source and DLQ retention are bounded by local disk monitoring; no automatic pruning in the learning profile.

Per-order ordering is guarded by `aggregateSequence`. If `n+1` arrives before `n`, persist it in an Order History `pending_order_event` table and acknowledge only after that commit. Later events for that order remain parked; other orders on the same Kafka partition continue. When `n` arrives, drain consecutive buffered events. After the timeout, report a visible gap and reconcile against the Orders outbox; either replay the missing source event or leave that order blocked. Never silently skip a sequence. An event below current sequence is a harmless duplicate only when ID/hash matches the inbox; otherwise quarantine it. Same event ID with different content is always a conflict.

Replay is a local operator CLI action authenticated by the local operator identity. It validates the corrected envelope and records an append-only audit row in the Order History database with source DLQ coordinate, original event ID/hash, corrected hash if applicable, operator subject, reason, timestamp and replay operation ID. Replay preserves original event ID; applied IDs with different hashes cannot be rewritten. Repeated replay operation IDs return the first result. Replay cannot reduce sequence or overwrite newer state.

## Projection rebuild and reconciliation

Create an isolated replacement projection database/namespace and a distinct consumer group. Record per-partition Kafka high-water offsets, replay from earliest, then consume until reaching those marks with lag zero. Capture a second high-water mark, catch up to it, verify reconciliation, and switch the active projection target in one short operation. On any failure, keep the old target active and mark the replacement failed. Report progress and lag to the operator and a stale/unavailable state to the UI.

Compare unique event IDs and payload hashes across retained Orders outbox rows, Kafka and projection inbox, plus current order counts/state/owner keys and monetary totals through Orders' public API or an explicitly documented owner-only SQL check. Current Orders rows do not prove every historical transition; full history can only be reconciled to the retained outbox/Kafka event set. State that limitation in command output and evidence.

## Operator command contract and fault injection

Implement these local commands so the manual guide is executable: `streaming-up`, `streaming-down`, `stream-status`, `stream-demo-poison`, `stream-replay --source-coordinate ... --corrected-payload-file ... --operation-id ... --reason ...`, `stream-rebuild [--dry-run|--inject-reconciliation-mismatch]`, `stream-reconcile`, and `stream-fault consumer-after-db-commit --once --order-id ...`. `restart <service>` supports `kafka-connect` and `order-history`. `stream-demo-poison` emits one deterministic invalid synthetic event and a corrected synthetic payload file in `/tmp`, and prints the source coordinate and a suggested operation ID; the file is deleted after manual checks. The replay command requires both a correction file and caller-supplied stable operation ID; rerunning with that same ID must return the original result. Rebuild failure injection changes only the candidate projection before reconciliation, must preserve the current active target, and the subsequent normal rebuild must succeed. Consumer crash injection terminates the consumer after projection/inbox commit but before offset commit, once; the consumer supervisor restarts and the inbox proves redelivery was a no-op. These commands and instrumentation are disabled outside the local integration profile.

## Local profile and resource budget

Keep `core` as the current commerce stack. Add an explicit `streaming` profile for Kafka, Connect and Order History; a documented full integration command starts both. Proposed initial bounds: Kafka heap 768 MiB/container 1 GiB; Connect heap 512 MiB/container 768 MiB; Order History heap 384 MiB/container 512 MiB; streaming additions capped at 2.5 GiB. Keep Docker allocation at or below the current 7.75 GiB baseline. Do not run Spark/lakehouse heavy jobs beside full commerce on the 16 GB Mac. These budgets are proposals until ARM64 startup, peak RSS, consumer throughput and concurrent checkout are measured. At design review time, Apache Kafka 4.3.1 is the latest supported stable release and its official image lists ARM64; Debezium 3.7.0.Final is the latest stable series and its release notes state it is built/tested with Kafka Connect and brokers 4.3.1. Pin these compatible versions only after confirming the chosen Connect container publishes an ARM64 image; otherwise build a reproducible local Connect image from the official Kafka base and official Debezium artifacts. Verify exact digests/licenses and runtime feasibility during implementation. No cloud services, hosted Schema Registry or Ollama container. Compose/Helm/operational scripts remain under `devops/`.

## Review checklist

1. Confirm CDC choice: Debezium Kafka Connect from Orders WAL rather than application polling.
2. Confirm JSON Schema compatibility in repository CI without a schema-registry service.
3. Confirm M06 scope is order history, leaving search, graph and lakehouse projections for later.
4. Review deterministic legacy backfill, snapshot/WAL overlap and restart acceptance.
5. Review gap parking, transactional DLQ/offset behavior, audited replay and privacy/key handling.
6. Review rebuild high-water/cutover, reconciliation limits and explicit resource budget/profile split.

## Required evidence

- Editable diagram: `event-flow.mmd`.
- Separate manual end-user checks: `manual-acceptance.md`.
- Review findings/resolutions: `design-review.md`.
- After review: service contracts and ADR for CDC/outbox choices.
