# S1-M08 — Graph, lakehouse and reporting

Status: Source implementation and automated/manual verification plans are authored. All M08 builds, tests and runtime checks are deferred until the Stage 1 development pass is complete.

Architecture proposal: [S1-M08 diagram](../../../architecture/stage-1/S1-M08.excalidraw). Implementation design: [design](design.md), [editable flow](flow.mmd), [review](design-review.md), [metrics/dashboard](dashboard-and-metrics.md), and [manual acceptance](manual-acceptance.md).

Initial technology decisions for implementation: Neo4j Community for bounded product/order relationships; Spark and Iceberg for replayable event facts; Trino for local SQL reporting. Analytics workloads are opt-in and selective on the 16 GB Mac. Source data is the public Orders lifecycle event envelope from Kafka, never another service's private database. Only privacy-reviewed allowlisted facts are projected.

Implementation includes a bounded local Neo4j graph projection/API, an idempotent Kafka-to-Iceberg Spark batch job, per-currency curated report tables, a Trino JDBC catalog, a read-only analytics API, and an operator dashboard in the storefront admin. Superset is an optional local dashboard studio. No build, test, or runtime capability is claimed as verified.
