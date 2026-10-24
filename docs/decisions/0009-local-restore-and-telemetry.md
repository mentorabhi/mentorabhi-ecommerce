# ADR 0009: Isolated local recovery and service health telemetry

Date: 2026-10-24
Status: Accepted for S1-M09 source implementation; runtime validation pending.

## Context

The local development environment is a single Docker host with PostgreSQL, Kafka and named volumes. It needs a repeatable database backup/restore exercise, coarse service availability visibility, and bounded local ingress without implying high availability.

## Decision

- Back up each PostgreSQL database in custom format, record file size and SHA-256, and keep output under ignored `devops/.local/backups/` with restrictive modes.
- Validate manifests and hashes before restore. Restore into a unique, isolated Compose project and volume; provision from repository SQL and remove the drill project/volume after success or failure.
- Apply Nginx request/body/connection bounds at the local ingress edge.
- Use a small internal-only readiness/TCP exporter, Prometheus `3.15.1` (Apache-2.0), and Grafana OSS `13.2.2` (AGPL-3.0-only) in an optional profile. Dashboard and retention are local-only. The `13.3.0` release-note signal had no matching `grafana/grafana` image tag; use the available stable multi-architecture `13.2.2` image.
- Keep stateless Helm deployment replica count configurable through `appReplicas`; PostgreSQL and Kafka remain singleton stateful components in this stage.
- Treat 24-hour RPO and 2-hour RTO as proposed drill targets. No objective is accepted as met before timed restore evidence.

## Consequences

Backup files contain personal/order data and are not encrypted by the backup script. The host must protect `.local/backups` with encrypted storage. Database backups omit Kafka topics, broker offsets, local volumes, and images; stream recovery has separate M06 procedures. Prometheus health telemetry does not provide app metrics, traces, or centralized logs. Multi-node failover remains future work.

## Sources

Version and license selection follows official [Prometheus releases](https://github.com/prometheus/prometheus/releases), [release support policy](https://prometheus.io/docs/introduction/release-cycle/), [Grafana stable image tags](https://hub.docker.com/r/grafana/grafana/tags), [Grafana license](https://github.com/grafana/grafana/blob/main/LICENSING.md), and [self-managed upgrade cadence](https://grafana.com/docs/grafana/latest/upgrade-guide/when-to-upgrade/). Architecture/review and verification limits are recorded in [S1-M09](../milestones/S1-M09/README.md).
