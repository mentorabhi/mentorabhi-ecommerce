# S1-M09 design — resilience, recovery and operational telemetry

Revision 2 · 2026-10-24 · Design and registry lock reviewed before implementation completion

## Goals and limits

1. Recover a local database snapshot into a disposable, isolated Compose project without touching the active commerce volume.
2. Keep host-bound ingress local, reject oversized API requests, and bound request rate and concurrent connections.
3. Expose service readiness and dependency availability on a small optional local dashboard.
4. Preserve configurable replicas/resources in Helm for larger machines and identify stateful single-node limitations clearly.

This local profile has one PostgreSQL instance, one Kafka broker, one host and local named volumes. It cannot provide node failure tolerance, replicated storage, zero-downtime database failover, or broker quorum recovery. A future larger-machine/Kubernetes deployment needs independent HA database and Kafka topologies.

## Decisions and evidence

- Use PostgreSQL custom-format per-database dumps (`pg_dump -Fc`) and SHA-256 manifests. Store them only in ignored `.local/backups/` with restrictive directory/file modes. Backups contain customer and order data; filesystem permissions are not encryption. Users should put the local backup directory on encrypted host storage.
- Create a separate uniquely named Compose project and volume for restore drills. Provision roles/databases, restore each dump under its owning role, verify schemas and table accessibility, then remove only the drill project/volume in a `finally` cleanup. The active `supersports` Compose project and its volumes are never target operands.
- Back up each PostgreSQL database sequentially as an independent `pg_dump`; this is not a cluster-wide atomic snapshot. The manifest timestamp brackets the dump set. Cross-database business consistency is checked after restore through M06/M08 reconciliation procedures.
- Bound each database dump and restore command to 30 minutes, the post-restore identity/table probe to two minutes, and isolated-project cleanup to two minutes. A timeout fails the local operation; backup timeouts remove the incomplete backup set.
- Use Nginx request body, request rate and connection limits on the loopback-bound storefront. Limits apply to Nginx-routed API URLs; direct internal service ports remain local development endpoints. Target values are safeguards and must be adjusted only from measured traffic.
- Add a tiny stdlib health exporter which probes public readiness endpoints and dependency TCP ports inside the Compose network. Prometheus scrapes it; Grafana provisions one service-health dashboard. This is availability telemetry only, not Java runtime, JVM, request latency histogram, database query, Kafka consumer lag, distributed traces or log aggregation.
- Pin Prometheus `3.15.1` (Apache-2.0; official release, 2026-10-21) and Grafana OSS `13.2.2` (AGPL-3.0-only; stable multi-platform image). A `grafana/grafana:13.3.0` image tag was not published, despite the release-note signal, so it is not used. OpenTelemetry Collector is not included because no trace/span exporter is instrumented in the applications. Official evidence: [Prometheus releases](https://github.com/prometheus/prometheus/releases), [Prometheus LTS/release cycle](https://prometheus.io/docs/introduction/release-cycle/), [Grafana stable image tags](https://hub.docker.com/r/grafana/grafana/tags), [Grafana license](https://github.com/grafana/grafana/blob/main/LICENSING.md), [Grafana release policy](https://grafana.com/docs/grafana/latest/upgrade-guide/when-to-upgrade/).
- Keep operational observability opt-in under a separate Compose profile; use local images and loopback host ports. No cloud telemetry or external alert receiver.
- Pin image index digests in `devops/images.lock.json` for Prometheus `3.15.1` (`sha256:fa3302279710be2f21a8301ec17a8b4f2301fd829bd113839b3b6b02b6f191a2`), Grafana `13.2.2` (`sha256:ac461fb352abc50da10a51c7d02462e9c05488f11f53f14b3ad79a8145f638a0`), and Python `3.13.17-slim` (`sha256:d98cc29d3266e535dd9da1099688d9cb3ca4753813571e071763d17725460962`); each registry index includes a `linux/arm64` manifest. The lock also pins M08 data-service image indexes; see the [M08 manifest record](../S1-M08/design.md#registry-manifest-lock-2026-10-24).
- Record proposed recovery objectives only: RPO 24 hours and RTO 2 hours for a documented local database restore. These are targets for the drill, not measured service levels.

## Design order

`M09` backup and restore design precedes scripts. The isolated restore project is reviewed against volume names and cleanup behavior before implementation. Ingress limits are applied at Nginx, not in checkout business rules. Telemetry reports observations and never becomes an authority for order or payment state.

## Verification boundary

Author unit tests for manifest/path safety, shell-script integration tests for backup/restore and exact cleanup, Nginx limit regression checks, health exporter tests, and Selenium checks for Grafana. Manual acceptance covers service status, URLs, restore into a disposable project, row/schema checks and cleanup. No backup/restore, load, build, runtime or test operation is permitted during the current development-first pass. M06 gates resume first once M09 development is complete.
