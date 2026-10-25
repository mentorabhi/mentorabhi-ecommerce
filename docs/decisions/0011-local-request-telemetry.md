# ADR 0011 — Local request telemetry

2026-10-25 · Accepted for S1-M12 source implementation; runtime acceptance pending.

R28 expands ADR 0009 beyond service health. Use the OpenTelemetry Java agent for eleven Java services, an internal Collector, Prometheus request metrics, Tempo traces and Loki safe request logs, visualized in existing Grafana with admin/admin. The profile is explicit on the 16 GB host. All telemetry storage/export remains local; no host ports for ingestion/backends. Default SDK-disabled app images keep normal commerce independent of telemetry.

Retain only bounded route/method/status and selected database operation metadata. Export only a dedicated safe request logger; drop raw exceptions/application messages, headers, query/body/SQL values, personal identifiers and other resource data. Preserve trace/span relationships. This intentionally limits centralized log scope. Unit/config source cannot prove actual privacy; sentinel and linked-signal runtime tests are required.

Pin release versions/digests and a checksum-verified agent artifact, with ARM64 metadata and licence records. Retention is configured at 24 hours for traces/logs with bounded queues/resources, not a fixed disk guarantee. Image-preserving lifecycle commands recreate only running Java apps and persist project-local selection. Python/browser instrumentation and multi-node telemetry availability remain outside this initial scope. See S1-M12 design, dependencies and manual guide for targets versus evidence.
