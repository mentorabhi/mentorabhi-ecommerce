# S1-M08 design — graph projection, lakehouse and reporting

Revision 1 · 2026-10-24 · Design before implementation

## Decisions and evidence

- **Graph:** self-managed Neo4j Community Edition, `2026.10.1`, image ARM64-compatible per Neo4j's supported-platform guidance. Use the open-source Community Edition (GPLv3); do not use the commercial Enterprise image. Neo4j's official Docker guide documents the current tag and Community image, while its requirements explicitly include Apple Silicon ARM64. Official sources: [Docker operations](https://neo4j.com/docs/operations-manual/current/docker/introduction/), [system requirements](https://neo4j.com/docs/operations-manual/current/installation/requirements/), [license](https://neo4j.com/legal-terms/).
- **Java graph driver:** `org.neo4j.driver:neo4j-java-driver:6.2.1`. Current driver documentation lists 6.2.1 and supports Neo4j 2026.x; use one long-lived driver and short bounded transactions. Sources: [driver install/compatibility](https://neo4j.com/docs/java-manual/current/install/), [current releases](https://neo4j.com/deployment-center/).
- **Lakehouse compute/format:** Spark `4.1.3` + Iceberg `1.12.0`. The latest Spark 4.2.0 is not selected because Iceberg 1.12's published Spark runtime is 4.1 and its 4.2 integration is still in progress. Spark official docs list stable 4.1.3 and 4.2.0; Iceberg's current quickstart explicitly pairs runtime `iceberg-spark-runtime-4.1_2.13:1.12.0`. Sources: [Spark stable releases](https://spark.apache.org/downloads/), [Iceberg quickstart](https://iceberg.apache.org/spark-quickstart/), [Iceberg release notes](https://iceberg.apache.org/releases/).
- **SQL serving:** Trino `484`, current stable release dated 2026-10-15; use the official `trinodb/trino:484` container and Iceberg JDBC catalog. Source: [official downloads](https://trino.io/download), [Iceberg JDBC catalog](https://trino.io/docs/current/object-storage/metastores.html).
- **Warehouse storage:** local shared filesystem volume by default. Spark writes Parquet-backed Iceberg tables; Trino reads the same volume. A dedicated PostgreSQL `lakehouse` database/role stores JDBC catalog metadata. This is entirely local and leaves a storage adapter boundary for later local S3-compatible or managed-service configuration; no cloud endpoint or credential is introduced.
- **Dashboard:** Superset `6.1.0` is the latest stable release identified; Superset 7 remains a release candidate on the Apache release page. It is a separate optional dashboard profile, not part of the core 16 GB startup. Source: [Apache Superset releases](https://github.com/apache/superset/releases).

The pinned registry manifest references below identify exact tags and ARM64 support. Local pulls/builds, service startup, memory and license acceptance remain unverified.

## Registry manifest lock (2026-10-24)

The configured OCI indexes were inspected from the official Docker registries before the consolidated test phase. `devops/images.lock.json` pins the index digests so Docker can select the host architecture. The observed indexes advertise `linux/arm64` for Neo4j 2026.10.1 (index `sha256:f238979f3c80da6f383f2e4fe91be4dc3580d7ee3b7edec83d0b8783c53b74a4`), Trino 484 (`sha256:2704eb53935af5e582d63d6033e9bf99d20c325e9b0e30b1016ef59a4773979f`), Spark 4.1.3 (`sha256:bf9d035a7c32a8ca46aa58d6348182ffd7d2dff6409206ecfbb3915ff1fef211`), and Superset 6.1.0 (`sha256:16b50bbef6648912a79e3293d418fefa743ce555d36c5af6b85d859119ed7f88`). Indexes are multi-platform and include `linux/amd64` as well. Registry manifests are not a substitute for local pull/build/runtime verification.

## Data ownership and flow

1. Kafka lifecycle topics are the sole operational source for analytics. Consumers preserve event ID, type/version, aggregate ID/sequence, timestamp, partition/offset and the allowlisted event payload. Do not read private Catalog, Orders, Payment or Inventory tables.
2. Iceberg raw events are append-only and deduplicated by event ID with source-coordinate lineage. Invalid or unsupported events are counted/quarantined, not silently coerced.
3. Curated order facts derive confirmed revenue from OrderAccepted/OrderConfirmed, and refunds from OrderRefundCompleted. Cancellations/returns keep their separate identities. Merchandise/tax/shipping/currency remain separate; no cross-currency sum is allowed. Reconciliation compares per-currency analytics totals to Orders and Payment owner APIs/test fixtures, with explicit timing/freshness.
4. Neo4j receives deterministic MERGE projections only: Product, SKU, Category, Order, and co-purchase relationships from OrderAccepted facts. Customer identity uses an opaque keyed subject digest only when needed for distinct counts; no name, address, contact, review or support content enters the graph.
5. A bounded relationship API returns curated paths with maximum depth, result count and execution timeout. Analytics and graph stores are rebuildable projections; neither is a commerce authority.

## Profiles and resource plan

Run graph projection/API, Spark batch ingestion, Trino/report API, and optional Superset as separate opt-in profiles/jobs. Spark is one-shot, capped at 1 GiB driver heap/1.5 GiB container, not an always-on cluster. Do not run Spark concurrently with Trino/Superset or other heavy profiles on the baseline Mac. Preserve a larger-machine profile with the same source and schemas. Measure RSS and runtime before changing any stated budget.

## Verification and limits

Add deterministic fixtures for duplicate/late/v1/v2 event ingestion, graph relationship validity and bounded traversal, financial per-currency reconciliation, rebuild from Kafka, freshness, and data deletion/privacy. Add SQL reports for gross confirmed sales, refunds, cancellations, net totals and best-selling products. Manual guide includes profile health, UI/SQL query steps, catalog/table counts, and reconciliation queries. All M08 test/build/runtime execution is deferred until Stage 1 development is complete.
