# S1-M06 manual end-user acceptance

Revision 2 · 2026-10-24 · Runnable checklist contract for the implemented M06 profile; execute only after implementation verification.

Use synthetic accounts/orders only. Do not paste personal data, bearer tokens or secrets into this file. Keep boxes unchecked until a person performs each action.

## 1. Start and health

- [ ] Start core commerce and the streaming profile from repository root:

  ```sh
  ./devops/scripts/supersports up
  ./devops/scripts/supersports streaming-up
  ./devops/scripts/supersports status
  ```

- [ ] Confirm healthy PostgreSQL, Keycloak, Catalog, Configuration, Pricing, Inventory, Customer, Orders, Payment Simulator, Fulfillment Simulator, Storefront, Kafka, Kafka Connect and Order History. Record image tags/digests from `status`; record Docker allocation from `./devops/scripts/supersports doctor`.
- [ ] Open storefront at http://localhost:3000 and operator UI at http://localhost:3000/admin. Kafka broker is loopback-only at `localhost:9092`; Connect REST is `http://localhost:8090`; Order History API readiness is `http://localhost:8089/actuator/health/readiness`.
- [ ] Run `./devops/scripts/supersports stream-status`. Confirm connector `orders-outbox` is RUNNING, database slot/WAL lag is bounded, topic `commerce.order.events.v1` exists, consumer lag reaches zero, and DLQ count is zero before creating the test event.
- [ ] Confirm events, Connect offsets, Kafka internal topics, Order History inbox/projection and DLQ survive restarting their containers. State which data persists in local volumes.

## 2. Customer order-history flow and ownership

- [ ] Register two separate customers through the storefront self-registration flow. Sign in as Customer A, complete an order with synthetic data and note the order ID from the order detail page.
- [ ] Open order history. Confirm the matching order appears after CDC/consumer processing and the page shows an update/freshness time.
- [ ] Repeat with Customer B. Confirm B sees only B's orders. Attempt direct API access to A's order ID as B; expect `404` (or the documented non-disclosing denial).
- [ ] Attempt a request that supplies `customerSubject`/`customerKey` as a query or body filter; expect `400`/`403`, with owner always derived from the verified token.
- [ ] Sign in with the local operator account and call the customer order-history API; expect `401`/`403`. Confirm operator login does not provide customer history access.
- [ ] Stop and start Order History using `./devops/scripts/supersports restart order-history`; confirm it catches up and does not add duplicate order cards or move an order to an older state.

## 3. CDC, Kafka and consumer recovery

- [ ] Inspect the topic key using the documented Kafka CLI command printed by `stream-status`. Confirm the key is the order ID, event ID/version/sequence are present, and no address, email, raw customer subject or payment instrument is present.
- [ ] Run `./devops/scripts/supersports restart kafka-connect` before publishing a new order event; create a synthetic order; restart Connect again after event publication. Confirm connector resumes from the durable offset and the unique event appears once in the projection inbox.
- [ ] Run `./devops/scripts/supersports stream-fault consumer-after-db-commit --once --order-id <synthetic-order-id>`. Confirm the consumer process exits at the documented boundary, supervisor restarts it, redelivery is deduplicated by event ID/hash, and the consumer group returns to zero lag.
- [ ] Confirm duplicate event ID with same payload is a no-op; same ID with a different payload hash is quarantined and does not change projection state.
- [ ] Confirm an intentionally delayed sequence is parked, blocks only that order, and drains after its missing predecessor arrives. Confirm unrelated order events continue through the same partition.

## 4. DLQ and replay

- [ ] Generate one synthetic poison event with `./devops/scripts/supersports stream-demo-poison`. Record the returned source coordinate, suggested operation ID, and corrected fixture path only in the local terminal.
- [ ] Run `./devops/scripts/supersports stream-status`; confirm one DLQ record includes source topic, partition, offset and error code, and the consumer resumes for unrelated orders.
- [ ] Replay using `./devops/scripts/supersports stream-replay --source-coordinate <topic:partition:offset> --corrected-payload-file <printed-fixture-path> --operation-id <suggested-operation-id> --reason "manual acceptance"`. Confirm the CLI identifies the local operator, writes one audit entry and the corrected event is applied once.
- [ ] Repeat the same command with the same operation ID. Confirm it returns the prior result, creates no duplicate projection and does not regress aggregate sequence.
- [ ] Confirm DLQ/replay data persists until explicit project reset; do not delete a shared volume as part of this checklist.

## 5. Projection rebuild and read-only database checks

- [ ] Run `./devops/scripts/supersports stream-rebuild --dry-run`; confirm it reports the active projection version, Kafka partition high-water marks and estimated replay counts without modifying active data.
- [ ] Run `./devops/scripts/supersports stream-rebuild --inject-reconciliation-mismatch`; confirm it fails reconciliation and the old projection remains active and readable. Then run the normal rebuild and confirm it succeeds.
- [ ] Run `./devops/scripts/supersports stream-rebuild`; observe progress, catch-up to the second high-water mark and cutover. Confirm the old target remains active if reconciliation fails; on success, storefront history remains available and matches before rebuild.
- [ ] Run `./devops/scripts/supersports stream-reconcile`. Expected: zero missing/extra unique event IDs, zero payload hash conflicts, zero ownership/state/financial mismatches, and a report that clearly limits historical validation to retained outbox events.
- [ ] Read database migration versions and aggregate counts using the local PostgreSQL owner account:

  ```sh
  docker exec supersports-postgres-1 psql -U postgres -d orders -c "SELECT version,description,success FROM flyway_schema_history ORDER BY installed_rank;"
  docker exec supersports-postgres-1 psql -U postgres -d orders -c "SELECT count(*) AS events, count(DISTINCT event_id) AS unique_ids, count(*) FILTER (WHERE event_id IS NULL OR aggregate_sequence IS NULL) AS incomplete FROM order_outbox;"
  docker exec supersports-postgres-1 psql -U postgres -d order_history -c "SELECT version,description,success FROM flyway_schema_history ORDER BY installed_rank;"
  docker exec supersports-postgres-1 psql -U postgres -d order_history -c "SELECT count(*) AS inbox_events, count(DISTINCT event_id) AS unique_ids FROM event_inbox;"
  docker exec supersports-postgres-1 psql -U postgres -d order_history -c "SELECT state,count(*) FROM order_history_projection GROUP BY state ORDER BY state;"
  ```

- [ ] Expected: source outbox event count equals unique source IDs; no incomplete legacy events or quarantine rows; history inbox has no duplicate event IDs; projection state/order totals match the reconciliation report. Use the table names documented by the final migrations if implementation names differ.
- [ ] Confirm all database reads above are owner/operator checks and that the Order History runtime role cannot connect to Orders DB. Confirm rebuild changed only the Order History-owned database.
- [ ] Run `./devops/scripts/supersports streaming-down`; verify the core storefront/admin remain healthy. Then stop the full stack with `./devops/scripts/supersports down` when finished.

## Human result

- Date/time and operator: ____________________
- Core/streaming image revision and Docker allocation: ____________________
- Outcome: Pass / Fail
- Reconciliation summary / issue references: ____________________
- Notes: ____________________
