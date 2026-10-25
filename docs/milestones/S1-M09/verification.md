# S1-M09 verification record

## Stage 1 live recovery and ingress acceptance — 2026-10-25

- `devops/scripts/supersports test --recovery`: two full integration passes each finished with 25/25 core and 6/6 streaming tests. The recovery segment confirmed configuration/migration state through service restart; all application APIs became unready while PostgreSQL was down and remained live; PostgreSQL reconnect restored readiness; Keycloak token issuance recovered. Full logs: `/tmp/supersports-stage1-final2.log` (local, not a repository artifact).
- `SUPERSPORTS_M09_LIVE_ACCEPTANCE=true PYTHONPATH=devops/scripts .venv/bin/python -m unittest devops.tests.test_resilience_integration devops.tests.test_ingress_limits -v`: 3/3 passed in 31.089 seconds. Backup/restore used an isolated disposable Docker project and restored all 13 owned databases; source Orders remained queryable. The Nginx rate test received 429 under concurrent burst while `/healthz` stayed available, and oversized request body returned 413.
- `SUPERSPORTS_M09_LIVE_ACCEPTANCE=true SE_OFFLINE=true .venv/bin/python -m unittest discover -s apps/storefront/tests -p test_ops_ui.py -v`: passed in 35.607 seconds. Initial browser check exposed Grafana's persisted first-run password-update prompt; Selenium now skips that optional prompt for the configured local demo admin, opens the provisioned health dashboard directly, and asserts its title and readiness panel.
- Restore drill is isolated and removed only its UUID project/network/volume. Backups remain local mode-restricted SQL dumps; they are not encrypted, cross-database atomic snapshots, or off-host disaster recovery.

M09 code/runtime checks above are green. Human operation of Grafana and the exact owner manual acceptance steps remain pending.

## Stage 1 verification restart — 2026-10-24

Before the full M06 acceptance pass, the management status command could not load the local credentials. The file contained the complete recognized `PRE_M07_SECRET_KEYS` set. `configure()` accepted that set in its version check but its per-line allowlist omitted `CDC_DB_PASSWORD`, `ORDER_HISTORY_DB_PASSWORD`, and `ORDER_HISTORY_OWNER_KEY`, so it rejected the migration before appending current keys.

- Added a regression for extending the known M06 credential set while preserving all existing values.
- Fixed line validation to accept only keys in current `SECRET_KEYS`; exact prior-version set matching remains the migration gate.
- `.venv/bin/python -m unittest devops.tests.test_manage.ConfigureTests.test_configure_extends_known_m06_credentials_without_rotating_them -v`: 1 passed.
- `.venv/bin/python devops/scripts/manage.py configure`: succeeded, adding missing local keys and retaining existing values; command did not print secret values.
- `.venv/bin/python devops/scripts/manage.py status`: all 15 active services healthy.

This is a focused setup regression, not an M09 full test/build/runtime acceptance. Broader Stage 1 verification continues from the M06 completion matrix.

## Consolidated suite refresh — 2026-10-25

Repository `devops/scripts/supersports unit` passed after the graph-down dependency regression was added: 94 Python tests discovered, 34 integration-only tests skipped in unit mode; analytics API 6/6, graph 3/3, health exporter 2/2, storefront Node freshness tests 2/2, and all Java module tests passed. M09 isolated restore/ingress tests passed 3/3; Grafana Selenium passed separately. Helm/Terraform deployment validators passed in the preceding consolidated run.

OpenTelemetry distributed request traces/latency and centralized searchable logs remain unimplemented. Prometheus/Grafana currently expose local health/readiness metrics. Owner-run Grafana/backup/restore manual acceptance remains pending; this is not a multi-node HA or off-host recovery claim.

A fresh profile-start check later on 2026-10-25 found Grafana's first navigation intermittently returned an empty response during startup. After startup, `/api/health` returned version 13.2.2 and `/api/search?query=SuperSports` returned the provisioned dashboard UID, but the Selenium dashboard navigation timed out twice under the current combined local profile load. This is recorded as an inconclusive fresh rerun; the earlier isolated Selenium pass remains the positive browser evidence. Profile-start latency/responsiveness needs another low-load owner or automated check.

## Low-load Grafana browser recheck — 2026-10-25 03:47 UTC

After the M06 snapshot probe, graph/analytics profiles remained stopped and only the observability profile was brought up. Grafana health returned version 13.2.2, the provisioned dashboard API returned its expected UID, and `SUPERSPORTS_M09_LIVE_ACCEPTANCE=true SE_OFFLINE=true .venv/bin/python -m unittest discover -s apps/storefront/tests -p test_ops_ui.py -v` passed 1/1 in 34.164 seconds. The prior combined-profile timeout is therefore resolved for the isolated low-load profile. Dashboard/backup owner manual checks remain pending.
