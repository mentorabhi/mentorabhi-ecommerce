# S1-M06 verification record

Revision 1 · 2026-10-24 · Automated and local runtime evidence. Human acceptance remains open.

## Environment

- Mac ARM64 (`aarch64`), Docker 29.8.0, Docker RAM allocation 7.75 GiB, Python 3.14.7 in repository `.venv`.
- Apache Kafka `4.3.1`, Debezium Connect `3.7.0.Final`, PostgreSQL `18.6`, and pinned application base images are recorded in `devops/images.lock.json`.
- Connect REST reports connector `supersports-orders-outbox` RUNNING and task 0 RUNNING. `order-history-v1` consumer lag was 0 on partitions 0, 1 and 2 after the test run.
- Fourteen runtime containers were healthy. One `docker stats --no-stream` snapshot summed to approximately 4,719 MiB RSS (about 4.61 GiB) against the 7.75 GiB Docker allocation. In that snapshot Kafka used 480.4 MiB, Connect 496.3 MiB, and Order History 425.3 MiB. A separate cold Connect startup reached approximately 770 MiB before settling near 549 MiB; its limit is now 1 GiB. These are observations, not peak/load measurements.

## Automated checks

Command: `SE_OFFLINE=true ./devops/scripts/ci`

- Compose configuration validation passed.
- Python operations and JSON Schema contract unit suite passed; JSON Schema validates all five supported event types, rejects incomplete sequence/privacy payloads, and validates the live outbox rows.
- Java unit suite passed: 84 tests, 0 failures/errors.
- Helm lint/render and intended negative cases passed. Terraform format/init/validate/test passed (3 tests); no cloud provisioning occurred.
- Core integration suite passed twice (22 tests per pass), before and after recovery checks.
- Recovery checks passed: application/migration state across service restart; readiness/liveness behavior and reconnection through PostgreSQL outage; identity token issuance recovered.
- Streaming integration passed twice in the original full CI; follow-up targeted reruns passed after adding the explicit database-private-table assertion and deterministic consumer crash test. The crash test waits for zero lag, arms the one-shot fault, checks out an order, observes the container restart, and verifies the projected sequence count equals `lastSequence` after redelivery. The earlier schema and owner-isolation assertions continue to run in that same integration journey.
- Selenium suite passed: 7 journeys, including customer login, asynchronous projected order list, opening an order, and order detail. The configuration test restores tax to 1800 even when an assertion fails.

## Database evidence

After the latest streaming integration/recovery run and test-created synthetic orders:

- Orders outbox: 122 events, 122 distinct event IDs, 0 rows missing event ID, sequence or customer key.
- Order History inbox: 122 events, 122 distinct event IDs; 46 projected orders.
- The source and inbox totals match; consumer lag is zero. Reconciliation here covers retained outbox/inbox counts and the tested customer projection path only. It is not the designed full historical replay/rebuild reconciliation.

## Open acceptance and limitations

- The owner must perform and record the separate [manual acceptance checklist](manual-acceptance.md).
- Peak memory, throughput and sustained lag under load have not been measured.
- Operator-audited poison correction/replay and isolated candidate projection rebuild/reconciliation/cutover remain unimplemented. Full M06 design completion is therefore open; do not represent those behaviors as tested.
- Follow-up after the initial full CI: `.venv/bin/python -m unittest discover -s devops/tests -p test_manage.py -v` passed (25 tests); the order-history Maven module passed six unit tests; the full streaming integration journey passed, including injected exit after database commit, container restart, replay deduplication and owner isolation. Full CI has not been rerun after this follow-up change.
- Review evidence is in [design-review.md](design-review.md). This report contains measured runtime facts separately from the deferred design proposal.
