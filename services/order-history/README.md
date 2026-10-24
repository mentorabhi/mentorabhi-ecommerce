# Order History service

This Spring Boot project owns the customer order-history read model and its PostgreSQL database. It consumes the versioned Orders outbox topic from local Kafka. It never reads the Orders database.

## Local profile

Start the full commerce stack and streaming services from repository root:

```sh
./devops/scripts/supersports streaming-up
./devops/scripts/supersports stream-status
```

Service readiness: `http://localhost:8089/actuator/health/readiness`. The storefront and operator UI are at `http://localhost:3000` and `http://localhost:3000/admin`.

## API and ownership

- `GET /api/v1/order-history` returns up to 100 orders owned by the verified customer JWT subject.
- `GET /api/v1/order-history/{orderId}` returns an owned projection or a non-disclosing 404.
- Caller-provided `customerSubject`, `customerKey` or `owner` list filters are rejected.
- The service maps verified customer subjects to a local HMAC key. The raw subject is not put into the event or projection tables.
- The API requires the `supersports-customer-api` audience; operator tokens do not have this audience.

## Delivery and data ownership

The consumer disables automatic Kafka commits. It applies a projection change and inbox row in one PostgreSQL transaction, then commits the source offset. Stable event IDs and payload hashes make same-payload redelivery a no-op and detect conflicting reuse. Per-order sequence gaps are persisted in `pending_order_event`; only that aggregate is parked. Invalid events are sent to the DLQ with their source offset in a Kafka transaction.

Orders PostgreSQL remains authoritative. Kafka Connect offsets/internal topics, Kafka records, the Order History database and its inbox survive container restart through local volumes. `supersports reset --confirm-reset supersports` removes local runtime volumes.

## Current scope and known work

Implemented: versioned envelope/backfill, Debezium CDC, event topic, durable inbox/projection, per-order sequence handling, owner-scoped reads, transactional poison-to-DLQ handling, deterministic consumer crash injection, and authenticated operator correction/replay. Consumer validation follows `contracts/orders/order-lifecycle-v1.schema.json`. Canonical hashes deduplicate formatting/numeric equivalents; legacy raw hashes remain available as evidence.

Local operator commands: `stream-demo-poison` and `stream-replay --source-coordinate ... --corrected-payload-file ... --operation-id ... --reason ...`. The CLI uses a transient non-web container, verifies the operator token, and records immutable audit plus resumable publication intent. See the [manual guide](../../docs/milestones/S1-M06/manual-acceptance.md) and [workflow detail](../../docs/milestones/S1-M06/operator-workflows.md).

Candidate projection rebuild/reconciliation/cutover remains unimplemented against the full reviewed M06 design.
