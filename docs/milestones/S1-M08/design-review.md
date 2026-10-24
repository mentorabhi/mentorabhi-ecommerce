# S1-M08 design review

Revision 1 · 2026-10-24 · Reviewed against R14/AE15, M06 Kafka contracts, the S1-M08 architecture diagram, 16 GB ARM64 baseline and no-cloud boundary.

- **Cross-service ownership:** analytics consumes published lifecycle events and never joins private service tables. Reconciliation uses narrow owner APIs or controlled test fixtures.
- **Money:** aggregate only within currency; define confirmed revenue and completed refunds separately; cancellation/refund events must not double-count.
- **Replay:** preserve event identity and Kafka coordinates; use idempotent writes; retain invalid-event counts/quarantine evidence; make graph and curated tables rebuildable.
- **Privacy:** omit addresses, contact data, ticket/review text and raw customer subjects. Use an opaque keyed digest only for explicitly approved distinct-customer metrics.
- **Compatibility:** Spark 4.1.3 is paired with Iceberg 1.12.0 because current Iceberg runtime documentation lists Spark 4.1; Spark 4.2 support is still being completed. Trino is pinned to current stable 484. Neo4j Community remains the GPLv3 ARM64 local graph choice.
- **Capacity:** all data services are optional; Spark runs as a bounded one-shot job. No dashboard/lakehouse process is added to core checkout startup.
- **Dashboard delivery:** the operator workspace has a first-party report dashboard and API for the standard metrics; Superset is a separate optional exploration/dashboard studio. This keeps core operations small while giving operators useful reports immediately.
- **Metric scope:** confirmed orders only contribute sales/AOV; completed refunds are deducted once for net sales; cancellation and return request counts remain distinct. Visitor conversion is excluded because no traffic event source exists.
- **Implementation review:** Kafka Debezium `after.payload` is unwrapped into the versioned lifecycle envelope. The lakehouse excludes the opaque customer subject and raw review/support content. Graph paths have fixed maximum depth, result bounds, and transaction timeout. Local Spark is a bounded one-shot job.
- **Residual deployment gate:** Neo4j, Spark, Trino and Superset image tags must have exact tested ARM64 digests in the image lock before profile deployment. The source uses stable version tags pending this deferred manifest pinning. Build/test/runtime execution remains deferred until all Stage 1 development is done.
