# ADR 0008: Local analytics and graph projections

Date: 2026-10-24  
Status: Accepted for S1-M08 source implementation; runtime validation pending.

## Context

S1 needs a relationship demonstration and ecommerce reporting without cloud services, cross-service private database reads, or a large always-on workload on the 16 GB ARM64 development Mac. Reports must keep currencies separate and avoid counting attempted orders or refunds as confirmed revenue.

## Decision

- Kafka lifecycle events are the operational input to rebuildable analytics projections.
- Neo4j Community stores a privacy-filtered product/SKU/order graph. A local API limits graph depth, result count and query time.
- A selective one-shot Spark 4.1.3 job writes deduplicated Iceberg facts to a local filesystem warehouse. Iceberg 1.12.0 is chosen because its published Spark runtime is for Spark 4.1.
- Trino 484 reads Iceberg through a dedicated PostgreSQL JDBC catalog. A read-only API exposes allowlisted ecommerce reports to the existing operator UI.
- The operator dashboard displays currency-specific confirmed sales, AOV, discounts, completed refunds, net sales, daily trend, product performance and separate cancellation/return-request counts.
- Superset 6.1.0 is optional and local for dashboard exploration; it is outside the default commerce profile. Its local login is `admin` / `admin` per the user's local authentication decision.
- No visitor conversion or abandonment metric is claimed until corresponding storefront events exist. No raw customer identity, address, contact, review or support text enters analytical stores.

## Consequences

The core commerce profile is unchanged; reporting, graph, and batch compute start separately. Reconciliation and resource measurements must be recorded during the deferred verification pass. Exact tested ARM64 image digests remain a deployment prerequisite; current source uses pinned version tags only. Superset's local metadata database is disposable/rebuildable and contains dashboard metadata, not commerce facts.

## Sources

Technology versions are grounded in official documentation referenced by [S1-M08 design](../milestones/S1-M08/design.md). Superset's [6.1 installation guide](https://superset.apache.org/admin-docs/6.1.0/installation/installation-methods/) describes Compose deployment and [official Docker builds support ARM64](https://superset.apache.org/admin-docs/6.1.0/installation/docker-builds/); Trino 484 [supports environment-backed connector secrets](https://trino.io/docs/current/security/secrets.html); Trino Python client 0.340.0 is the stable package recorded for this implementation.
