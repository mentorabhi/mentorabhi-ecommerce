# S1-M06 verification record

Revision 3 · 2026-10-24 · Targeted replay verification passed after the prior full CI; human acceptance remains open.

## Environment

- Mac ARM64 (`aarch64`), Docker 29.8.0, Docker RAM allocation 7.75 GiB, Python 3.14.7 in repository `.venv`.
- Apache Kafka `4.3.1`, Debezium Connect `3.7.0.Final`, PostgreSQL `18.6`, and pinned application base images are recorded in `devops/images.lock.json`.
- Connect REST reports connector `supersports-orders-outbox` RUNNING and task 0 RUNNING. `order-history-v1` consumer lag was 0 on partitions 0, 1 and 2 after the test run.
- Fourteen runtime containers were healthy. One `docker stats --no-stream` snapshot summed to approximately 4,719 MiB RSS (about 4.61 GiB) against the 7.75 GiB Docker allocation. In that snapshot Kafka used 480.4 MiB, Connect 496.3 MiB, and Order History 425.3 MiB. A separate cold Connect startup reached approximately 770 MiB before settling near 549 MiB; its limit is now 1 GiB. These are observations, not peak/load measurements.

## Automated checks

Command: `SE_OFFLINE=true ./devops/scripts/ci`

- Compose configuration validation passed.
- Python operations and JSON Schema contract unit suite passed; JSON Schema validates all five supported event types, rejects incomplete sequence/privacy payloads, and validates the live outbox rows.
- Java unit suite passed: 84 tests, 0 failures/errors, including the six Order History tests after crash-injector changes.
- Python unit discovery reported 49 test methods, with 22 live core methods and the streaming class intentionally skipped. The actual executed unit cases were 27 (25 operations and two event-contract cases); live integration ran separately below. Earlier text labeling all 49 as unit cases was inaccurate.
- Helm lint/render and intended negative cases passed. Terraform format/init/validate/test passed (3 tests); no cloud provisioning occurred.
- Core integration suite passed twice (22 tests per pass), before and after recovery checks.
- Recovery checks passed: application/migration state across service restart; readiness/liveness behavior and reconnection through PostgreSQL outage; identity token issuance recovered.
- Streaming integration passed twice in this full CI run after adding the explicit database-private-table assertion and deterministic consumer crash test. The crash test waits for zero lag, arms the one-shot fault, checks out an order, observes the container restart, and verifies the projected sequence count equals `lastSequence` after redelivery. Schema and owner-isolation assertions run in the same integration journey.
- Selenium suite passed: 7 journeys, including customer login, asynchronous projected order list, opening an order, and order detail. The configuration test restores tax to 1800 even when an assertion fails.

## Database evidence

After the latest replay integration run and test-created synthetic orders:

- Orders outbox: 153 events, 153 distinct event IDs.
- Order History inbox: 153 events; 57 projected orders, zero pending sequence gaps, four replay audits and zero unpublished replay deliveries.
- The source and inbox totals match; consumer lag is zero. Reconciliation here covers retained outbox/inbox counts and the tested customer projection path only. It is not the designed full historical replay/rebuild reconciliation.

## Open acceptance and limitations

- The owner must perform and record the separate [manual acceptance checklist](manual-acceptance.md).
- Peak memory, throughput and sustained lag under load have not been measured.
- Isolated candidate projection rebuild/reconciliation/cutover remains unimplemented. Full M06 design completion is open; do not represent that behavior as tested.
- Full CI was rerun after the crash recovery change and passed end to end: `SE_OFFLINE=true ./devops/scripts/ci`. It rebuilt the ARM64 images, validated Compose/Helm/Terraform, ran Java/Python unit checks, two core integration passes, two streaming passes with injected crash recovery, recovery checks, and seven Selenium journeys. That full run predates the replay follow-up below; candidate rebuild commands remain pending.
- Review evidence is in [design-review.md](design-review.md). This report contains measured runtime facts separately from the deferred design proposal.

## Replay follow-up verification

After the last full CI, the replay slice added operator authentication, append-only audit, durable delivery intent, source-partition publication, canonical fingerprints and strict consumer contract validation. The following checks passed against the rebuilt ARM64 Order History image:

- Dockerized Maven `test`/image `verify`: 11 Order History tests. New tests first failed because replay types did not exist, then fingerprint/contract regressions failed against the incomplete behavior, then passed after implementation.
- `.venv/bin/python -m unittest discover -s devops/tests -p 'test_*.py' -v`: 31 unit cases passed (53 test methods discovered; 22 live core methods plus the streaming class intentionally skipped).
- `SUPERSPORTS_INTEGRATION=1 SUPERSPORTS_PROJECT=supersports .venv/bin/python -m unittest discover -s devops/tests -p test_streaming_integration.py -v`: two journeys passed in 138.132 seconds. This includes consumer commit/offset crash recovery, operator/customer isolation, interruption before publication, interruption after publication/before receipt persistence, identical retry receipts, changed-operation conflict, refusal to rewrite applied history, formatting-safe redelivery, and append-only audit enforcement.
- `SE_OFFLINE=true .venv/bin/python -m unittest discover -s apps/storefront/tests -p test_customer_history_ui.py -v`: one Selenium journey passed in 4.590 seconds.
- Compose validation and `git diff --check` passed. No dependency version was added or changed.

The full CI has not yet been rerun after this replay slice. [Implementation review and coverage limits](replay-review.md) record the manual scan and unavailable independent review capability. Operator manual acceptance remains separate.
