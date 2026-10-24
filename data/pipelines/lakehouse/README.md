# Local commerce lakehouse

One-shot Spark job that reads the Orders lifecycle Kafka topic, validates the immutable event envelope, and writes append-only Iceberg raw events plus currency-separated order/refund facts. It is deliberately invoked on demand; do not run alongside the full commerce profile on the 16 GB baseline Mac.

The Spark runtime and Iceberg packages are pinned in `devops/compose/analytics.yaml`. The local warehouse is a named volume shared with Trino. Only allowlisted fields are projected. The job never connects to a commerce database. The `services/analytics-api` serves the operator dashboard; Superset is an optional SQL/dashboard studio.

## Invocation

Use `devops/scripts/supersports analytics-up` to start the opt-in graph/reporting profile and `devops/scripts/supersports analytics-run` to ingest/replay the Kafka history. The built-in operator dashboard is at `/admin` → Analytics. Runtime and reconciliation checks are in `docs/milestones/S1-M08/manual-acceptance.md`; they remain unverified until the consolidated Stage 1 verification pass.
