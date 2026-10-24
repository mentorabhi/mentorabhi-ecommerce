# S1-M06 manual end-user acceptance

Revision 5 · 2026-10-24 · Adds isolated rebuild, reconciliation and cutover checks. Run manually after automated checks; leave boxes unchecked until performed by a person.

Use synthetic accounts and orders only. Do not paste personal data, bearer tokens or secrets into this file.

## 1. Services and storefront

- [ ] Follow [DBeaver host inspection checks](../../setup/database-access.md) to verify service health, host database login, UI continuity and read-only database queries.
- [ ] On Orders, confirm the connected-status notice and checked time appear when streaming is caught up. Stop streaming and confirm an unavailable notice while owned Orders records still load; restore streaming afterwards. Gap/delay demonstrations require the isolated probe, which remains planned.

- [ ] From the repository root run `./devops/scripts/supersports streaming-up`, then `./devops/scripts/supersports stream-status`.
- [ ] Confirm healthy PostgreSQL, Keycloak, Catalog, Configuration, Pricing, Inventory, Customer, Orders, Payment Simulator, Fulfillment Simulator, Storefront, Kafka, Kafka Connect and Order History using `./devops/scripts/supersports status`.
- [ ] Open [SuperSports storefront](http://localhost:3000), sign in or self-register, and open Orders. Confirm the order list loads and shows the asynchronous status notice.
- [ ] Open an order. Confirm products, amounts, status, delivery address and Indian locale render. Use a second customer account to open the same order URL; it must return the non-disclosing not-found result.
- [ ] Confirm the operator account cannot access customer order history and customer accounts cannot access the operator workspace APIs.
- [ ] Restart Order History with `./devops/scripts/supersports restart order-history`. Confirm it returns healthy, history remains available, and event counts do not grow from duplicates.
- [ ] In Docker Desktop, stop Kafka Connect and then Kafka. While both are stopped, submit a synthetic checkout and confirm Orders accepts it. Start Kafka, wait for healthy, then start Kafka Connect. Confirm the Debezium connector/task return to RUNNING, the order advances to `FULFILLMENT_SCHEDULED`, and Orders and History show the same event sequence without duplicates. Automated repeat: `SUPERSPORTS_INTEGRATION=1 SUPERSPORTS_PROJECT=supersports .venv/bin/python -m unittest discover -s devops/tests -p test_streaming_integration.py -k cdc_resumes -v`.
- [ ] Run `./devops/scripts/supersports streaming-down`. Confirm the storefront and operator workspace remain available. Restart with `./devops/scripts/supersports streaming-up` when finished.

Storefront URL: http://localhost:3000 · Operator UI: http://localhost:3000/admin · Kafka: `kafka:9092` inside Compose (use the local CLI; no host port) · Connect REST: http://localhost:8090 · Order History readiness: http://localhost:8089/actuator/health/readiness

## 2. CDC and Kafka checks

- [ ] Follow the [Kafka UI guide](../../setup/kafka-ui.md) at http://localhost:8091 to inspect brokers, event messages, partitions, consumer lag and Debezium connector status from the host browser.

- [ ] In `./devops/scripts/supersports stream-status`, confirm `supersports-orders-outbox` connector and task are RUNNING and topics `commerce.order.events.v1` (3 partitions) and `commerce.order.events.dlq.v1` (1 partition) exist.
- [ ] Place a new synthetic order in the storefront. Confirm it first appears as an accepted order and then its status advances asynchronously.
- [ ] Read a small sample from `commerce.order.events.v1` using the local Kafka console consumer. Confirm the key is the order ID and payload fields include event ID, event version and aggregate sequence. Confirm payloads do not contain a delivery address, email address, raw customer subject or payment instrument.
- [ ] Restart Kafka Connect once more and place another synthetic order. Confirm the new order is projected once and the consumer catches up.
- [ ] Wait until `stream-status` shows zero consumer lag, then run `./devops/scripts/supersports stream-fault consumer-after-db-commit --once --next-event`. Place one synthetic order. Confirm Order History restarts once, the order appears after recovery, and its projected event sequences have no duplicates. The fault marker applies to the next valid event only.
- [ ] For each transactional DLQ boundary, first run `./devops/scripts/supersports stream-dlq-fault --once --stage before-commit` (then repeat later with `after-commit`) and immediately run `./devops/scripts/supersports stream-demo-poison`. Record its coordinate, then confirm Order History restarts and `stream-status` returns to zero lag. In Kafka UI, set the DLQ view to `read_committed` semantics if available and confirm exactly one DLQ record for that source coordinate; inspect the source consumer group and confirm its committed offset is past that coordinate. Replay the poison using section 3 so the retained-history reconciliation can pass. Repeat for the other boundary. Automated live probe: `SUPERSPORTS_INTEGRATION=1 SUPERSPORTS_PROJECT=supersports .venv/bin/python -m unittest discover -s devops/tests -p test_streaming_integration.py -k dlq_and_source -v`.
- [ ] Run the isolated ordering/browser regression: `SUPERSPORTS_INTEGRATION=1 SUPERSPORTS_PROJECT=supersports .venv/bin/python -m unittest discover -s devops/tests -p test_streaming_integration.py -k isolated_gap -v`. It creates a temporary History database, one-partition topic and group, then removes only those generated resources in cleanup. Observe owner A move from DELAYED to BLOCKED while owner B stays CURRENT; the browser must show the warning and A’s current Orders record. After predecessors arrive, confirm the gap drains, duplicates do not inflate history, and conflicting content does not alter the order. During the same test, stop the probe and confirm the browser displays UNAVAILABLE while still showing A’s current owned record. Finish by confirming the ordinary Order History container is healthy and `stream-status` reports zero lag.

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

## 4. Projection rebuild and reconciliation

- [ ] Run `./devops/scripts/supersports stream-reconcile`. Confirm `ok: true`, no errors, matching retained event/order facts and reported currency totals. Totals include all current order states and are not recognized sales. Read the historical-retention limitation in the output.
- [ ] Record the active database and consumer group from `stream-status`. Run `./devops/scripts/supersports stream-rebuild --dry-run`. Confirm `DRY_RUN_VERIFIED`, matching candidate facts, first/second high-water marks for all three partitions, and a private receipt file under `devops/.local/stream-rebuilds/`. The saved active target must still be the previous pair.
- [ ] Run `./devops/scripts/supersports stream-rebuild --inject-reconciliation-mismatch`. This intentionally changes one amount in the isolated candidate. Expect a nonzero exit, `RECONCILIATION_FAILED`, and an amount mismatch. Confirm `stream-status` still names the original target and the customer history UI still loads.
- [ ] Run `./devops/scripts/supersports stream-rebuild`. Confirm `ACTIVE`, successful reconciliation, a new database/group pair and a healthy Order History container. The target is saved after service readiness; a startup failure recreates the previous pair.
- [ ] Sign in as the same customer and open an existing order. Confirm amounts, products, ownership and sequence history remain correct. Place a new synthetic order and wait for `FULFILLMENT_SCHEDULED`; confirm the new consumer continues after the captured offsets. The other customer must still receive 404 for the order.
- [ ] Run `stream-reconcile` again and confirm it passes on the new target. Restart Order History, run `stream-status`, and confirm the saved target survives restart.
- [ ] Inspect replay audit/delivery rows in the active database using section 5. Confirm the pre-rebuild operation IDs, actors, reasons, timestamps and publication receipts are retained. Candidates and previous projection databases are retained for diagnosis and consume local disk; reset removes runtime volumes after explicit confirmation.

## 5. Read-only database checks

Run these local checks after the test order has completed. Use only synthetic test records.

Set `SUPERSPORTS_HISTORY_DB` to the active database printed by `stream-status`. It starts as `order_history`; successful rebuilds select a generated `order_history_r_...` database.

```sh
SUPERSPORTS_HISTORY_DB='<active database from stream-status>'
docker exec supersports-postgres-1 psql -U postgres -d orders -c "SELECT version,description,success FROM flyway_schema_history ORDER BY installed_rank;"
docker exec supersports-postgres-1 psql -U postgres -d orders -c "SELECT count(*) AS events, count(DISTINCT event_id) AS unique_ids, count(*) FILTER (WHERE event_id IS NULL OR aggregate_sequence IS NULL OR customer_key IS NULL) AS incomplete FROM order_outbox;"
docker exec supersports-postgres-1 psql -U postgres -d "$SUPERSPORTS_HISTORY_DB" -c "SELECT version,description,success FROM flyway_schema_history ORDER BY installed_rank;"
docker exec supersports-postgres-1 psql -U postgres -d "$SUPERSPORTS_HISTORY_DB" -c "SELECT count(*) AS inbox_events, count(DISTINCT event_id) AS unique_ids FROM event_inbox;"
docker exec supersports-postgres-1 psql -U postgres -d "$SUPERSPORTS_HISTORY_DB" -c "SELECT state,count(*) FROM order_history_projection GROUP BY state ORDER BY state;"
docker exec supersports-postgres-1 psql -U postgres -d "$SUPERSPORTS_HISTORY_DB" -c "SELECT operation_id,source_coordinate,event_id,operator_subject,reason,created_at FROM order_history_replay_audit ORDER BY created_at DESC LIMIT 10;"
docker exec supersports-postgres-1 psql -U postgres -d "$SUPERSPORTS_HISTORY_DB" -c "SELECT operation_id,published_topic,published_partition,published_offset,published_at FROM order_history_replay_delivery ORDER BY published_at DESC NULLS FIRST LIMIT 10;"
docker stats --no-stream
```

- [ ] Confirm all outbox events have unique event IDs, sequence numbers and opaque customer keys; the inbox has unique event IDs; projected orders and status counts match the customer UI.
- [ ] Confirm the Order History service database role cannot connect to the Orders database. Its history API derives ownership from the verified customer token and rejects caller-supplied owner filters.
- [ ] Record Docker allocation with `./devops/scripts/supersports doctor` and the observed container memory from `docker stats --no-stream`. Treat these as a point-in-time observation, not a peak-load result.

## Scope still pending

Commands above are implemented. Remaining M06 acceptance includes broader source/consumer failure-boundary evidence, sequence-gap demonstrations, sustained load/freshness measurements and owner manual results. The separate acceptance matrix records the open gates; do not treat this guide as a completed human test record.

## Human result

- Date/time and operator: ____________________
- Core/streaming image revision and Docker allocation: ____________________
- Outcome: Pass / Fail
- Notes / issue references: ____________________
