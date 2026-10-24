# S1-M06 manual end-user acceptance

Revision 4 · 2026-10-24 · CDC, customer history, crash recovery and audited poison replay. Run manually after automated checks; leave boxes unchecked until performed by a person.

Use synthetic accounts and orders only. Do not paste personal data, bearer tokens or secrets into this file.

## 1. Services and storefront

- [ ] From the repository root run `./devops/scripts/supersports streaming-up`, then `./devops/scripts/supersports stream-status`.
- [ ] Confirm healthy PostgreSQL, Keycloak, Catalog, Configuration, Pricing, Inventory, Customer, Orders, Payment Simulator, Fulfillment Simulator, Storefront, Kafka, Kafka Connect and Order History using `./devops/scripts/supersports status`.
- [ ] Open [SuperSports storefront](http://localhost:3000), sign in or self-register, and open Orders. Confirm the order list loads and shows the asynchronous status notice.
- [ ] Open an order. Confirm products, amounts, status, delivery address and Indian locale render. Use a second customer account to open the same order URL; it must return the non-disclosing not-found result.
- [ ] Confirm the operator account cannot access customer order history and customer accounts cannot access the operator workspace APIs.
- [ ] Restart Order History with `./devops/scripts/supersports restart order-history`. Confirm it returns healthy, history remains available, and event counts do not grow from duplicates.
- [ ] Restart Kafka Connect with `./devops/scripts/supersports restart kafka-connect`. Confirm its connector task returns to RUNNING and newly checked out orders appear in history.
- [ ] Run `./devops/scripts/supersports streaming-down`. Confirm the storefront and operator workspace remain available. Restart with `./devops/scripts/supersports streaming-up` when finished.

Storefront URL: http://localhost:3000 · Operator UI: http://localhost:3000/admin · Kafka: localhost:9092 · Connect REST: http://localhost:8090 · Order History readiness: http://localhost:8089/actuator/health/readiness

## 2. CDC and Kafka checks

- [ ] In `./devops/scripts/supersports stream-status`, confirm `supersports-orders-outbox` connector and task are RUNNING and topics `commerce.order.events.v1` (3 partitions) and `commerce.order.events.dlq.v1` (1 partition) exist.
- [ ] Place a new synthetic order in the storefront. Confirm it first appears as an accepted order and then its status advances asynchronously.
- [ ] Read a small sample from `commerce.order.events.v1` using the local Kafka console consumer. Confirm the key is the order ID and payload fields include event ID, event version and aggregate sequence. Confirm payloads do not contain a delivery address, email address, raw customer subject or payment instrument.
- [ ] Restart Kafka Connect once more and place another synthetic order. Confirm the new order is projected once and the consumer catches up.
- [ ] Wait until `stream-status` shows zero consumer lag, then run `./devops/scripts/supersports stream-fault consumer-after-db-commit --once --next-event`. Place one synthetic order. Confirm Order History restarts once, the order appears after recovery, and its projected event sequences have no duplicates. The fault marker applies to the next valid event only.

## 3. Audited poison correction and replay

- [ ] Ensure the streaming stack is healthy and at least one synthetic order is projected. Run `./devops/scripts/supersports stream-demo-poison`. It corrupts the version of an existing event, waits for the DLQ, and returns `sourceCoordinate`, `operationId` and `correctedPayloadFile`. The demo does not create another commerce order.
- [ ] Copy those three values into the command below, keeping the same reason and operation ID on every retry. Local operator sign-in uses the ignored admin-login file; no token or password is printed.

```sh
./devops/scripts/supersports stream-replay --source-coordinate '<sourceCoordinate>' --corrected-payload-file '<correctedPayloadFile>' --operation-id '<operationId>' --reason 'manual poison version correction'
```

- [ ] Confirm the receipt reports `PUBLISHED`, preserves the event ID and lists the destination partition/offset. Repeat the exact command and confirm the same receipt returns. Publication is asynchronous; wait for zero lag and confirm the customer history still has one copy of each event sequence.
- [ ] In the database checks below, confirm exactly one immutable audit row exists for the operation ID, with the verified operator subject, reason and source coordinate. Its separate delivery row must have publication coordinates/time.
- [ ] If interrupted, retry with the same operation ID, correction and reason. A queued delivery is resumed; publication before receipt persistence may redeliver safely. An already applied event with changed content is rejected rather than rewritten. A changed reason or correction under an existing operation ID conflicts.
- [ ] Delete the returned temporary correction file after checks. Retained DLQ and audit records remain available for investigation; they are not deleted by replay.

## 4. Read-only database checks

Run these local checks after the test order has completed. Use only synthetic test records.

```sh
docker exec supersports-postgres-1 psql -U postgres -d orders -c "SELECT version,description,success FROM flyway_schema_history ORDER BY installed_rank;"
docker exec supersports-postgres-1 psql -U postgres -d orders -c "SELECT count(*) AS events, count(DISTINCT event_id) AS unique_ids, count(*) FILTER (WHERE event_id IS NULL OR aggregate_sequence IS NULL OR customer_key IS NULL) AS incomplete FROM order_outbox;"
docker exec supersports-postgres-1 psql -U postgres -d order_history -c "SELECT version,description,success FROM flyway_schema_history ORDER BY installed_rank;"
docker exec supersports-postgres-1 psql -U postgres -d order_history -c "SELECT count(*) AS inbox_events, count(DISTINCT event_id) AS unique_ids FROM event_inbox;"
docker exec supersports-postgres-1 psql -U postgres -d order_history -c "SELECT state,count(*) FROM order_history_projection GROUP BY state ORDER BY state;"
docker exec supersports-postgres-1 psql -U postgres -d order_history -c "SELECT operation_id,source_coordinate,event_id,operator_subject,reason,created_at FROM order_history_replay_audit ORDER BY created_at DESC LIMIT 10;"
docker exec supersports-postgres-1 psql -U postgres -d order_history -c "SELECT operation_id,published_topic,published_partition,published_offset,published_at FROM order_history_replay_delivery ORDER BY published_at DESC NULLS FIRST LIMIT 10;"
docker stats --no-stream
```

- [ ] Confirm all outbox events have unique event IDs, sequence numbers and opaque customer keys; the inbox has unique event IDs; projected orders and status counts match the customer UI.
- [ ] Confirm the Order History service database role cannot connect to the Orders database. Its history API derives ownership from the verified customer token and rejects caller-supplied owner filters.
- [ ] Record Docker allocation with `./devops/scripts/supersports doctor` and the observed container memory from `docker stats --no-stream`. Treat these as a point-in-time observation, not a peak-load result.

## Scope still pending

Candidate projection rebuild/reconciliation/cutover remain unimplemented. Do not attempt `stream-rebuild` or `stream-reconcile`; those commands do not exist yet. Poison correction/replay and deterministic consumer crash injection are implemented and covered above and in the streaming integration suite.

## Human result

- Date/time and operator: ____________________
- Core/streaming image revision and Docker allocation: ____________________
- Outcome: Pass / Fail
- Notes / issue references: ____________________
