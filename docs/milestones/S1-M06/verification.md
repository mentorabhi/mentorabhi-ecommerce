# S1-M06 verification record

Revision 4 · 2026-10-24 · Full CI after replay/rebuild passed; explicit remaining acceptance is in [the matrix](acceptance-matrix.md).

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
