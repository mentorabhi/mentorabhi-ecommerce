# S1-M09 manual acceptance — reliability and operations

Status: Implementation source is present; all automated, runtime and end-user checks are pending the consolidated Stage 1 verification pass.

## Services and UI

1. Record the current Compose project, service list, active profiles, and branch/commit. Confirm core storefront and API services are healthy.
2. Start `devops/scripts/supersports observability-up`; open Prometheus at `http://localhost:9090` and Grafana at `http://localhost:3001`. Sign in with local `admin` / `admin` and open the provisioned SuperSports service health dashboard. Kafka is expected up only when the streaming profile is active.
3. Confirm health exporter reports ready/up for each expected active service. Stop one disposable service and confirm its gauge changes to down; restore it and confirm recovery.
4. Send a burst of requests to a harmless read endpoint and confirm normal use works and excessive requests receive HTTP 429. Confirm an oversized request is rejected and health/static pages still load.

## Database recovery

1. Run `devops/scripts/supersports backup`; record the backup manifest and verify each listed database has a checksum and non-zero dump where expected.
2. Run `devops/scripts/supersports restore-drill <backup-directory>`. Confirm it prints the isolated project name, restores into the dedicated disposable service, verifies each connected database and its application table count (including a zero-table database when it was empty at backup time), then cleans only that project's container and volume.
3. Confirm active `supersports` PostgreSQL databases, orders, inventory and Kafka offsets remain unchanged by the drill. Verify no credentials appear in backup manifest or logs. Remember the per-database dumps are sequential rather than one atomic cluster snapshot.
4. Restore a single corrupted/missing dump in the disposable project and confirm the drill fails with a useful database/file error while cleanup still completes.

Automated sources: `devops/tests/test_recovery_operations.py`, `devops/tests/test_resilience_integration.py`, `devops/tests/test_ingress_limits.py`, `services/health-exporter/tests/test_probe.py`, and `apps/storefront/tests/test_ops_ui.py`. Set `SUPERSPORTS_M09_LIVE_ACCEPTANCE=true` only for the later isolated live acceptance run.

## Database and records

Check representative row counts in `catalog`, `orders`, `payment`, `inventory`, `reviews` and `support` before and after the drill. Compare pre/post source manifest hashes and verify the active project remains available. Record actual drill start/end time, restored database list, checksum failures, cleanup outcome and observed host memory.

RPO 24 hours and RTO 2 hours are proposed objectives only. Record actual measured values and any discrepancy separately; do not mark them met based on script presence.
