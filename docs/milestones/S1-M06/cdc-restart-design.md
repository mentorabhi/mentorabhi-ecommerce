# CDC and broker restart probe

Revision 1 · 2026-10-24 · Design before implementation

## Goal

Exercise the durable Orders outbox and Debezium PostgreSQL logical-decoding position while Kafka Connect and Kafka are unavailable. A synthetic order is accepted during the outage; after broker recovery and connector restart, its complete event history must reach the existing owner-scoped projection exactly once, and the active History consumer group must return to zero lag.

## Scope and safety

- Use the existing local `supersports` integration stack and synthetic checkout-test-customer account.
- Reuse the existing inventory/catalog checkout path, so assertions include the authoritative Orders rows and events instead of fabricated CDC records.
- Stop only `kafka-connect` and `kafka`; keep PostgreSQL, Orders, and Order History running. Kafka stop can cause transient History readiness/freshness changes; restore the broker in `finally` and wait for all health checks.
- No topic, database, connector offset, slot, or volume is deleted or recreated. This probe verifies resume from retained WAL and Kafka offsets, not snapshot/WAL overlap; overlap remains a separate gate.
- The checkout is idempotent under a generated unique request key. Assertions poll bounded deadlines and compare persisted outbox event IDs with the projected order's event sequence.

## Procedure and pass conditions

1. Confirm the connector/task are RUNNING and History lag is zero.
2. Stop Connect and Kafka. Submit one ordinary synthetic checkout while Kafka is stopped. Assert HTTP 202 and at least the checkout's initial event is committed in the Orders outbox.
3. Start Kafka and wait for health. Start Connect and wait for connector and task RUNNING.
4. Wait for the checkout to reach `FULFILLMENT_SCHEDULED`; inspect Orders outbox event IDs and History inbox/timeline for the same order. Require matching IDs, sequence `1..lastSequence`, no duplicate IDs, and zero lag across the three source partitions.
5. Confirm no unrelated order ownership data appears in the customer response. Leave the stack healthy.

## Failure handling

The test uses `try/finally` to start Kafka and Connect if any assertion fails. It does not roll back an accepted synthetic order or delete its evidence. A failed test prints ordinary unittest diagnostics; operator follow-up uses `supersports status`, `stream-status`, and container logs.

## Limits

This proves one controlled restart interval on the currently retained dataset. It does not establish prolonged WAL capacity, high throughput, offset retention beyond configured limits, broker quorum recovery, or consistent-snapshot/WAL overlap correctness. The local profile has one broker, so no multi-broker fault tolerance is implied.
