# S1-M06 verification record

## Full 1,000-customer history regression — 2026-10-25

The confirmed synthetic dataset exposed two scale/timing defects in the previously written live probes: the PostgreSQL aggregate snapshot exceeded the 384 MiB database limit, and the Order History inspection operator was killed with exit 137 at its 512 MiB container limit. The snapshot now emits one JSON row per source event/order. The selective streaming Order History cap/heap are 768/512 MiB, with the remaining 256 MiB reserved for JVM native memory. A sampled operator run used about 370 MiB; the resident consumer peaked at about 487 MiB of 768 MiB. These are point samples, not load/peak measurements.

- `stream-reconcile`: PASS against 35,830 retained outbox/Kafka/inbox/timeline events and 17,855 Orders rows; 20 quarantined poison coordinates had matching retained DLQ evidence and 36 replay audits/deliveries; zero reconciliation errors. The report explicitly limits conclusions to retained history and current order facts.
- `test_cdc_projection_and_tenant_scoped_read_api`: PASS after correcting its poll predicate to wait for all three checkout lifecycle events before asserting sequence deduplication.
- `test_z_isolated_rebuild_failure_dry_run_cutover_and_new_event_delivery`: PASS in 375.057 seconds with the full dataset; dry-run and injected mismatch preserved the active target, then the candidate rebuilt, reconciled, cut over and received a new checkout.
- Full `devops/scripts/supersports test` rerun: 25 core integration tests PASS; all six streaming tests PASS in 807.392 seconds. The first attempt's gap scenario failed only after the class-level JWT expired late in the 15-minute suite; the scenario now refreshes both identities at entry, and both blocked/unavailable Selenium paths passed in the rerun.
- One-shot DB-commit-before-offset redelivery did not create duplicate per-order sequence facts. CDC broker+Connect outage, both transactional DLQ crash boundaries, sequence gap isolation/ownership, poison replay audit/idempotency, and post-rebuild delivery all passed.

The separate `test --recovery` command performs a further application restart, PostgreSQL outage/readiness drill and a second full integration run. Its final log is in `/tmp/supersports-stage1-final2.log`; append its terminal result before treating the recovery rerun as complete. Snapshot/WAL overlap, sustained throughput/concurrency, longer Kafka/WAL retention, and owner manual acceptance remain distinct acceptance gates.

## Isolated ordering, timed-gap, ownership and UI fallback probe · 2026-10-24

- The existing reviewed [`freshness-and-ordering.md`](freshness-and-ordering.md) design was implemented as one serialized live integration scenario. It creates an owner B synthetic checkout if necessary, copies retained synthetic event envelopes into a disposable one-partition topic, starts an isolated Order History consumer/database with an 8-second gap threshold, and restores the normal service in `finally` while deleting only UUID-scoped probe resources.
- `SUPERSPORTS_INTEGRATION=1 SUPERSPORTS_PROJECT=supersports .venv/bin/python -m unittest discover -s devops/tests -p test_streaming_integration.py -k isolated_gap -v`: 1 integration test passed in 73.098 seconds. A sequence 3 was parked while B's event stream projected; A reported `DELAYED`, then `BLOCKED`; B reported `CURRENT` with zero owned gaps. Publishing A sequences 1 and 2 drained to 3. A duplicate left the inbox count at three; changed content under the same event ID was quarantined and left `lastSequence=3`.
- Both real storefront Selenium journeys passed while the isolated probe was active: `BLOCKED` warning with A's current Orders fallback, and `UNAVAILABLE` warning/fallback while the probe service was stopped. The direct nginx proxy also returned the expected `BLOCKED` state before browser execution.
- `SE_OFFLINE=true .venv/bin/python -m unittest discover -s apps/storefront/tests -p test_customer_history_ui.py -v`: the routine customer-history journey passed in 6.380 seconds; the two probe-only Selenium methods were correctly skipped outside their isolated integration context. Owner visual/manual acceptance remains separate. This controlled single-partition demonstration does not measure general throughput.

## CDC and broker restart probe · 2026-10-24

- Reviewed design, flow and owner review: [`cdc-restart-design.md`](cdc-restart-design.md), [`cdc-restart-flow.mmd`](cdc-restart-flow.mmd), [`cdc-restart-review.md`](cdc-restart-review.md).
- `SUPERSPORTS_INTEGRATION=1 SUPERSPORTS_PROJECT=supersports .venv/bin/python -m unittest discover -s devops/tests -p test_streaming_integration.py -k cdc_resumes -v`: 1 live test passed in 135.883 seconds. Kafka and Connect were stopped, a checkout was accepted and persisted in Orders outbox during the outage, then Kafka was started before Connect. The connector/task recovered, History reached `FULFILLMENT_SCHEDULED`, source outbox event IDs/sequences exactly matched inbox rows with contiguous aggregate sequence, and consumer lag returned to zero.
- The test restored both dependencies in `finally` and left its synthetic order/outbox/event records intact. This is a single-node, one-interval observation; snapshot/WAL overlap, longer WAL-retention and load are not proved.
- Human Docker Desktop execution remains pending in [`manual-acceptance.md`](manual-acceptance.md).

## Transactional DLQ commit-boundary probe · 2026-10-24

- Reviewed design/flow: [`dlq-crash-design.md`](dlq-crash-design.md), [`dlq-crash-flow.mmd`](dlq-crash-flow.mmd); review notes in [`design-review.md`](design-review.md).
- `.venv/bin/python -m unittest devops.tests.test_manage -q`: 27 passed. Dockerized Order History Maven tests: 20 passed after adding the crash-injector tests. `git diff --check` passed before the focused live rerun.
- `SUPERSPORTS_INTEGRATION=1 SUPERSPORTS_PROJECT=supersports .venv/bin/python -m unittest discover -s devops/tests -p test_streaming_integration.py -k dlq_and_source -v`: 1 test passed in 95.081 seconds. Both pre-commit and post-commit process halts recovered, each source coordinate had exactly one read-committed DLQ record, each corresponding group offset advanced past its source record, and the poison correction was published and drained.
- The broader four-journey streaming discovery exercised projection ownership, both crash points, audited replay and rebuild. The first three journeys passed; rebuild stopped at initial reconciliation because six older retained DLQ poison records at offsets 100–105 were unresolved in the persistent local history. This exposed a real data-set condition; it is not counted as a passing rebuild run. Two new crash-probe poison records were corrected and replayed by the test.
- The arm command clears only the matching fired marker on a fresh explicit arm; an already-armed marker is still rejected. This makes the one-shot probe repeatable across local reruns without weakening its one-event firing behavior.
- Human execution remains pending in [`manual-acceptance.md`](manual-acceptance.md).

## Latest freshness and host-access checkpoint — 2026-10-24

Implemented observed freshness (`CURRENT`, `DELAYED`, `BLOCKED`, `UNAVAILABLE`), owner-scoped pending gaps and storefront fallback to owned Orders records. The [design/review](freshness-and-ordering.md) precedes implementation; its isolated runtime probe remains planned.

- Pinned Maven image, `mvn -B -ntp test` in Order History: 19 tests passed.
- Pinned Node image, `node --experimental-strip-types --test tests/order-freshness.test.ts`: two tests passed.
- `.venv/bin/python -m unittest discover -s devops/tests -p test_database_access.py -v`: four passed.
- Same discovery command for `test_manage.py`: 26 passed.
- `SUPERSPORTS_INTEGRATION=1 SUPERSPORTS_PROJECT=supersports .venv/bin/python -m unittest discover -s devops/tests -p test_core_integration.py -v`: 23 passed in 39.083 seconds, including native host PostgreSQL authentication and loopback bindings.
- `SE_OFFLINE=true .venv/bin/python -m unittest discover -s apps/storefront/tests -p test_customer_history_ui.py -v`: one journey passed in 4.044 seconds, including connected banner and layout within the measured narrow viewport. Chrome's minimum window width means this is not proof of a 390-pixel viewport.
- Rebuilt/deployed History and Storefront; all 14 containers healthy after integration/restart checks.

No full CI rerun, isolated gap/outage evidence, DBeaver GUI setup or human manual acceptance is claimed. See [host setup and human checks](../../setup/database-access.md). Remaining milestone gates in the matrix stay open.

## Host Kafka UI addition — 2026-10-24

Added Kafbat UI v1.5.0 by digest, with Linux ARM64 manifest, to the Compose `streaming` profile. It binds to `127.0.0.1:8091`, connects to the existing Kafka broker and Debezium Connect endpoints, and runs read-only. The image is Apache-2.0; GitHub update checking, dynamic configuration and MCP are disabled. Resource limit 512 MiB/0.5 CPU, Java heap 256 MiB.

- Rendered Compose profile unit tests: two passed, covering opt-in profile, loopback binding, dependencies, image digest, read-only access and resource limit.
- Runtime host API checks: two passed. `/actuator/health` UP; cluster ONLINE/read-only; broker 1; seven topics; event topic has three partitions and retained messages; a message stream returned a MESSAGE event; consumer groups and the active rebuild group were listed; Debezium connector and task RUNNING.
- Selenium host-browser check passed in 2.000 seconds; cluster overview rendered.
- Runtime Docker sample: 271 MiB of 512 MiB cap; Compose reports healthy. This is a point observation, not a peak measurement.
- Compose config validation and existing 26 `test_manage.py` unit cases passed. No full CI rerun.

Host URL: http://localhost:8091. User manual checks remain open in [the Kafka UI guide](../../setup/kafka-ui.md). Read-only mode is an application-level safeguard; it does not configure Kafka ACLs.

Revision 5 · 2026-10-24 · Full rebuild CI plus focused tombstone/numeric-replay follow-up passed; remaining acceptance is in [the matrix](acceptance-matrix.md).

## Focused follow-up after rebuild checkpoint

After full CI at `3d84ca5`, two narrow edge cases were found and fixed: null Kafka values aborted diagnostic hashing, and replay identity rejected integer-equivalent sequence formatting such as `1.0` versus `1`. Both new regression tests were observed failing first (`NullPointerException` and `REPLAY_IDENTITY_CHANGE` respectively), then passed after the fixes. Existing non-null fingerprints and identity-change guards remain covered.

The rebuilt/deployed Order History image passed all 15 module tests. A live operator probe replayed a retained correction with floating-point integer sequence representation, returned `PUBLISHED`, returned the identical receipt on retry, and left the projection at 190 events/70 orders. Follow-up `stream-reconcile` passed with 11 audits and five resolved poison records; the customer history Selenium journey passed in 4.891 seconds. The tombstone case is a focused index/contract unit test, not an injected live commerce event. Unresolved malformed records remain explicit reconciliation failures.

The full repository CI below predates these two small follow-ups; it was not repeated after them. Verification after the fixes was scoped to the affected Java module, image build/readiness, live operator/reconciliation behavior and customer history UI.

## Latest full CI and rebuild verification

Command: `SE_OFFLINE=true ./devops/scripts/ci` (exit 0). Current pinned dependencies are unchanged. The run included:

- 81 Java tests across nine modules, counted once per standalone Maven summary: Catalog 10, Configuration 12, Pricing 13, Inventory 13, Customer 4, Orders 10, Payment 4, Fulfillment 2, Order History 13. Docker image build test reruns are excluded from this total. This is the authoritative latest count; earlier recorded aggregate counts are preserved below as historical reports.
- 40 executed Python unit cases: 26 operations/target tests, two event-contract cases, six reconciliation/control-path cases, and six operator CLI/lock cases. Discovery reported 62 test methods; 22 live core methods and the streaming class were intentionally skipped during unit discovery and explicitly invoked against Docker below.
- Compose validation, Helm lint/render/negative checks, Terraform format/init/validate plus three native tests passed; no cloud provisioning.
- Core integration passed twice, 22 tests each (37.609 and 39.858 seconds).
- Streaming integration passed twice, three journeys each (248.843 and 259.483 seconds). Each pass exercises consumer commit/offset crash recovery, audited replay with publication-boundary failures, and rebuild dry-run/mismatch/success followed by a new checkout reaching `FULFILLMENT_SCHEDULED` on the new target.
- Application restart, database readiness/liveness/reconnection and identity token recovery checks passed.
- All seven Selenium journeys passed in 40.662 seconds, including owner-scoped customer history after cutover.

The earlier targeted rebuild run passed all three journeys in 256.815 seconds. New reconciliation and target/index tests were first observed failing before their implementations existed, then passed. Readiness-failure rollback is covered by a control-path unit test; the live mismatch probe verifies preservation of the serving target. These are distinct evidence scopes.

Post-CI `stream-reconcile` returned `ok: true`, 190 unique retained events, 70 orders, five resolved poison records, ten replay audits and no reconciliation errors. It compared exact content/ownership/state/line/money facts, not only counts. Reported order totals were INR 32,247,935 minor units across all current states, not recognized sales. The active saved target is a generated `order_history_r_...` database with its corresponding generated group; inspect the local target via `stream-status`.

Memory sampling used repository `.venv` Python and repeated `docker stats --no-stream` during the full run. From 11:11:45 to 11:26:40 UTC, 210 samples recorded a maximum 5,237.09 MiB for SuperSports containers (15 containers at that sample) and 5,331.09 MiB across all running Docker containers. The host reports 17,179,869,184 bytes (16 GiB), with Docker allocated 7.75 GiB. Sampling sleeps two seconds after each Docker query, so this is a sampled maximum for this CI workload and can miss shorter spikes. It does not establish sustained/concurrent throughput or host/VM overhead capacity. Raw logs and samples remain ignored under `devops/.local/`.

The complete design is still open for the explicit source/DLQ transaction crash windows, delayed/gapped delivery and timed-gap UI behavior, broker-outage freshness, sustained/concurrent resource/lag measurements and separate human checks. See [implementation review](rebuild-review.md), [manual acceptance](manual-acceptance.md), and [completion audit](acceptance-matrix.md).

## Environment

- Mac ARM64 (`aarch64`), Docker 29.8.0, Docker RAM allocation 7.75 GiB, Python 3.14.7 in repository `.venv`.
- Apache Kafka `4.3.1`, Debezium Connect `3.7.0.Final`, PostgreSQL `18.6`, and pinned application base images are recorded in `devops/images.lock.json`.
- The initial streaming slice observed connector `supersports-orders-outbox` and task 0 RUNNING, with the original `order-history-v1` group at zero lag. Rebuilds now use generated groups; obtain the current pair and lag from `stream-status`.
- Fourteen runtime containers were healthy. One `docker stats --no-stream` snapshot summed to approximately 4,719 MiB RSS (about 4.61 GiB) against the 7.75 GiB Docker allocation. In that snapshot Kafka used 480.4 MiB, Connect 496.3 MiB, and Order History 425.3 MiB. A separate cold Connect startup reached approximately 770 MiB before settling near 549 MiB; its limit is now 1 GiB. These are observations, not peak/load measurements.

## Earlier crash-recovery CI record (before replay/rebuild)

Command: `SE_OFFLINE=true ./devops/scripts/ci`

- Compose configuration validation passed.
- Python operations and JSON Schema contract unit suite passed; JSON Schema validates all five supported event types, rejects incomplete sequence/privacy payloads, and validates the live outbox rows.
- The earlier narrative recorded 84 aggregate Java tests without a preserved per-module breakdown here. The authoritative latest total is the 81 tests counted once per module at the top of this record; image-build reruns are not added to that total.
- Python unit discovery reported 49 test methods, with 22 live core methods and the streaming class intentionally skipped. The actual executed unit cases were 27 (25 operations and two event-contract cases); live integration ran separately below. Earlier text labeling all 49 as unit cases was inaccurate.
- Helm lint/render and intended negative cases passed. Terraform format/init/validate/test passed (3 tests); no cloud provisioning occurred.
- Core integration suite passed twice (22 tests per pass), before and after recovery checks.
- Recovery checks passed: application/migration state across service restart; readiness/liveness behavior and reconnection through PostgreSQL outage; identity token issuance recovered.
- Streaming integration passed twice in this full CI run after adding the explicit database-private-table assertion and deterministic consumer crash test. The crash test waits for zero lag, arms the one-shot fault, checks out an order, observes the container restart, and verifies the projected sequence count equals `lastSequence` after redelivery. Schema and owner-isolation assertions run in the same integration journey.
- Selenium suite passed: 7 journeys, including customer login, asynchronous projected order list, opening an order, and order detail. The configuration test restores tax to 1800 even when an assertion fails.

## Database evidence

Historical replay-slice snapshot before rebuild work:

- Orders outbox: 153 events, 153 distinct event IDs.
- Order History inbox: 153 events; 57 projected orders, zero pending sequence gaps, four replay audits and zero unpublished replay deliveries.
- Those source/inbox totals matched with zero lag. That earlier check covered counts and the customer path; the latest full reconciliation above compares retained content and rebuilt state.

## Open acceptance and limitations

- The owner must perform and record the separate [manual acceptance checklist](manual-acceptance.md).
- The CI sampled memory maximum is recorded above. Sustained throughput/concurrent load and lag remain unmeasured.
- Candidate rebuild/reconciliation/cutover is now implemented and tested; the full M06 design still has the acceptance gaps listed in the matrix.
- Earlier full CI after crash recovery passed; the newer full run at the top of this record also covers replay and rebuild.
- Review evidence is in [design-review.md](design-review.md). This report contains measured runtime facts separately from the deferred design proposal.

## Replay follow-up verification

After the last full CI, the replay slice added operator authentication, append-only audit, durable delivery intent, source-partition publication, canonical fingerprints and strict consumer contract validation. The following checks passed against the rebuilt ARM64 Order History image:

- Dockerized Maven `test`/image `verify`: 11 Order History tests. New tests first failed because replay types did not exist, then fingerprint/contract regressions failed against the incomplete behavior, then passed after implementation.
- `.venv/bin/python -m unittest discover -s devops/tests -p 'test_*.py' -v`: 31 unit cases passed (53 test methods discovered; 22 live core methods plus the streaming class intentionally skipped).
- `SUPERSPORTS_INTEGRATION=1 SUPERSPORTS_PROJECT=supersports .venv/bin/python -m unittest discover -s devops/tests -p test_streaming_integration.py -v`: two journeys passed in 138.132 seconds. This includes consumer commit/offset crash recovery, operator/customer isolation, interruption before publication, interruption after publication/before receipt persistence, identical retry receipts, changed-operation conflict, refusal to rewrite applied history, formatting-safe redelivery, and append-only audit enforcement.
- `SE_OFFLINE=true .venv/bin/python -m unittest discover -s apps/storefront/tests -p test_customer_history_ui.py -v`: one Selenium journey passed in 4.590 seconds.
- Compose validation and `git diff --check` passed. No dependency version was added or changed.

This replay-only evidence predates the latest full CI at the top of this record. [Implementation review and coverage limits](replay-review.md) record the manual scan and unavailable independent review capability. Operator manual acceptance remains separate.

## Consolidated Stage 1 rerun — 2026-10-25 02:50 UTC

- `devops/scripts/supersports test --recovery` had completed earlier in this verification pass: two full integration runs, each 25/25 core and 6/6 streaming tests; PostgreSQL outage/reconnect readiness and liveness, application restart persistence, and Keycloak token recovery passed. Full terminal log: `/tmp/supersports-stage1-final2.log` (local evidence, not committed).
- Final `stream-reconcile` after storefront and data milestones: 35,973 retained events; 17,896 Orders; INR total 16,533,201,681 minor units; USD total 23,078,898 minor units; 29 poison coordinates; 48 replay audits; zero errors. The reconciliation is bounded to retained local Kafka/WAL and current source records.
- Live Kafka topic has three partitions; Order History offsets equal high-water marks 12,159 / 11,840 / 12,062 (zero lag). Debezium connector and task report RUNNING. Broker count remains one.
- Full automated test inventory and M06 live probes are recorded above. Snapshot/WAL overlap, sustained concurrent checkout/throughput, extended WAL/offset retention, and human owner acceptance are still open. The `test --recovery` result supersedes the earlier note that its terminal outcome awaited append.

## Debezium consistent snapshot/WAL overlap — 2026-10-25 03:46 UTC

The reviewed isolated probe passed on the pinned local PostgreSQL, Kafka 4.3.1 and Debezium 3.7.0.Final stack:

```sh
SUPERSPORTS_INTEGRATION=1 SUPERSPORTS_CDC_SNAPSHOT_OVERLAP=1 SUPERSPORTS_PROJECT=supersports \
  .venv/bin/python -m unittest discover -s devops/tests -p test_streaming_integration.py \
  -k initial_snapshot_overlaps_concurrent_wal_changes -v
```

Result: 1 passed in 45.408 seconds. The test seeded 100,000 compact rows, waited until the topic had a nonzero partial snapshot, then concurrently updated 500 existing rows and inserted 500 rows. It consumed and folded 101,000 keyed Kafka records. Each updated key had both an initial `r` and subsequent `u`; each inserted key had a `c`. The final folded 100,500-row state exactly matched the disposable source table, including values and payloads. The test also confirmed the ordinary Orders connector configuration and both Commerce topic high-water marks did not change. UUID-scoped connector, database, publication and topic cleanup completed in the passing run. No production Commerce records were altered.

The full local snapshot run observed 100,000 initial rows and 1,000 concurrent changes; it is not a sustained throughput or long-retention benchmark. Longer WAL/offset retention and sustained concurrent checkout measurements remain open.
