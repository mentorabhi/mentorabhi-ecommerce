# S1-M09 — Reliability, scaling and recovery

Status: Automated local verification is complete for the implemented recovery, all-13-database isolated restore, ingress-limit and health-dashboard scope. Owner-run manual acceptance remains open. Distributed OpenTelemetry traces/latency and centralized searchable logs are not implemented; see [verification](verification.md).

Inputs: [architecture proposal](../../../architecture/stage-1/S1-M09.excalidraw), [design](design.md), [editable flow](flow.mmd), [review](design-review.md), [manual acceptance](manual-acceptance.md), and [ADR 0009](../../decisions/0009-local-restore-and-telemetry.md).

Scope: local Docker recovery, permission-restricted database backups (not cryptographic encryption), isolated restore drills, Nginx request limits, local health telemetry, and scale-out configuration for a future larger host. This milestone does not make single-node PostgreSQL/Kafka highly available.

The implementation includes per-database SHA-256 dumps, bounded operations and isolated restore checks, loopback Prometheus/Grafana health reporting, Nginx API limits and configurable stateless Helm replicas. Prometheus/Grafana/Python and M08 data-service image indexes are pinned in `devops/images.lock.json`; registry manifests include ARM64. Measured test outcomes and limitations are in [verification](verification.md); these checks do not establish multi-node HA, encrypted backup, off-host DR, or the proposed RPO/RTO targets.
