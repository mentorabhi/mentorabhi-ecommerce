# devops — infrastructure and operations project

All infrastructure, container builds, deployment and operational automation live here. Catalog and Configuration remain independently buildable projects under services/.

## Prerequisites and startup
Read [local prerequisites](../docs/setup/prerequisites.md). Use the repository .venv; Java/Maven execute in pinned containers. Docker must be running. Existing host Ollama is a Nova prerequisite and is not part of this Compose profile.

Run from the repository root:
```sh
devops/scripts/supersports doctor
devops/scripts/supersports configure
devops/scripts/supersports validate
devops/scripts/supersports unit
devops/scripts/supersports up
devops/scripts/supersports test
```

configure creates or preserves private random credentials in ignored devops/.local/bootstrap.env (0600; directory 0700). It never prints them or silently rotates existing passwords. Do not print Compose's resolved configuration: it contains environment secrets.
up builds both service images, starts dependencies/services, applies owner migrations and waits for health. Repeated starts preserve databases and the imported realm.

Loopback endpoints:
- Catalog readiness: http://127.0.0.1:8081/actuator/health/readiness
- Configuration readiness: http://127.0.0.1:8082/actuator/health/readiness
- Local Keycloak: http://localhost:8180 (bootstrap administrator username bootstrap-admin; password remains in the private local file).
- Protected APIs: GET /api/v1/catalog/status (customer/catalog-admin), GET /api/v1/configuration (platform-admin).
There is no storefront or configuration editing UI yet. PostgreSQL has no published host port.

The synthetic users customer, catalog-admin and platform-admin use separate generated passwords. The regression script obtains tokens in memory; it never logs credentials/tokens. The password-grant CLI client is a local fixture, not the future browser authentication flow.

## Verification and local delivery
```sh
# Unit suites: Python operational behavior and both independent Java projects.
devops/scripts/supersports unit
# Real identity, authorization, migrations, database isolation, network bindings.
devops/scripts/supersports test
# Restart persistence, DB outage/liveness/readiness, token issuance recovery.
devops/scripts/supersports test --recovery
# Helm lint/render/negative schema gates and Terraform built-in tests.
.venv/bin/python devops/scripts/check_deployment.py
# Local CI-equivalent pipeline; no remote account required.
devops/scripts/ci
```

unit writes reports to each service's ignored target/surefire-reports via containerized Maven. Initial credential/configuration fixtures are migration/realm-owned; business catalog seeds arrive in S1-M03.
Core dependency/application image references and deployment-validator tools are pinned in images.lock.json. Container build contexts exclude credentials, .venv, docs and target outputs.

## Release and rollback
```sh
devops/scripts/supersports release local-v1
devops/scripts/supersports release local-v2
devops/scripts/supersports rollback local-v1
```
release builds immutable local version tags, deploys, runs live regressions and records exact image IDs in ignored devops/.local/releases-supersports.json only after success. Existing recorded versions cannot be overwritten. rollback accepts only a recorded verified release and restores its exact application image IDs; it does not revert database schema/data. Bootstrap schema v1 is additive/compatible. A failed release is not recorded; inspect status and roll back to a known release. No remote image publication occurs.

## Stop, status and reset
```sh
devops/scripts/supersports status
devops/scripts/supersports down
# Destructive: discards only this project's runtime volumes; preserves credentials.
devops/scripts/supersports reset --confirm-reset supersports
```
down preserves data. reset needs the explicit matching project name; never use it for routine shutdown. Optional --project supersports-<suffix> selects a separate named project, but the default host ports mean profiles run sequentially. These commands never prune unrelated containers/images/volumes. Build caches are preserved.

## Optional M08 analytics and M09 operations

These profiles are separate from core startup. Analytics URLs and acceptance steps are in `docs/milestones/S1-M08/manual-acceptance.md`.

```sh
devops/scripts/supersports analytics-up
devops/scripts/supersports analytics-run
devops/scripts/supersports graph-up
devops/scripts/supersports dashboard-studio-up
devops/scripts/supersports observability-up
devops/scripts/supersports backup
devops/scripts/supersports restore-drill devops/.local/backups/<backup-directory>
```

Prometheus is loopback-only at `http://localhost:9090`; Grafana is `http://localhost:3001` with local demo login `admin` / `admin`. Backups stay in ignored `devops/.local/backups/`; restrict and protect that host directory because it contains personal/order data. `restore-drill` checks the manifest, restores into a unique disposable Compose project and removes only that project's volume. See the M09 manual guide for end-user verification. RPO/RTO remain proposed until a timed restore drill is performed.

## Alternate deployment and limitations
See [Helm chart](helm/supersports/README.md), [Terraform skeleton](terraform/README.md) and [the deployment lesson](../docs/lessons/S1-M02.md).
Helm rendering is not proof of a successful Kubernetes deployment. Terraform's built-in state record is a local specification skeleton, not infrastructure provisioning. Stop Compose before a kind exercise. No cloud provider is configured.
Keycloak uses local development mode and loopback transport. Production hardening, full telemetry, supply-chain scans/SBOM gates and broader recovery objectives belong to later release milestones; passing bootstrap tests is not a security certification.
