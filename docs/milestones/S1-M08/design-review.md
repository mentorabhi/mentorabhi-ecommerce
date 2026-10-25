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

## Consolidated verification review — 2026-10-24

Source inspection found the projections used a raw Debezium table topic/envelope, whereas M06 routes expanded public envelopes to `commerce.order.events.v1`. Correct both consumers to the public contract, validate supported versions/fields before projection, and quarantine invalid source coordinates without retaining raw contact data. Share a standard-library public-contract validator under `contracts/`. Project co-purchases within one order and increment each pair once in an atomic, idempotent order transaction; the initial cross-order traversal is unsuitable for the larger demo dataset. Align Trino's JDBC catalog name with Spark's `local`, enable its documented local filesystem adapter, and test actual reads. Sources: [Trino local filesystem](https://trino.io/docs/current/object-storage/file-system-local.html), [Iceberg JdbcCatalog](https://github.com/apache/iceberg/blob/main/core/src/main/java/org/apache/iceberg/jdbc/JdbcCatalog.java). These corrections preserve the reviewed ownership and privacy boundary.

Port review: History already owns host port 8089. Trino moves to loopback port 8096; Docker-internal reporting continues to use `trino:8080`. Historical port proposals are superseded by this dated correction.

## Reconciliation and local resource review — 2026-10-25

- Kafka lifecycle events can contain Java `Instant` timestamps with 7–9 fractional digits. Python runtimes differ in parsing fractions beyond microseconds, so the shared validator now validates a normalized six-digit fraction while preserving the original envelope and timestamp in the lakehouse. Regression coverage exercises both nanosecond offsets and `Z` notation.
- The first full replay exposed 411 valid coordinates previously quarantined by the timestamp parser plus 29 intentionally malformed version-999 poison records. Current source acceptance is correct after the validator fix. The quarantine table is now rebuilt as a replayable projection of current contract results on each batch; this clears stale false rejects and retains current poison coordinates. Trino remains read-only. A Spark-side targeted merge-delete attempt failed on Spark 4.1's Iceberg source attribute binding and was replaced with the reviewed full-rebuild approach.
- On the 16 GB ARM64 host with 7.75 GiB Docker allocation, running Spark beside analytics/graph and optional observability/UI profiles can terminate a batch with exit 137. A bounded run succeeded after stopping graph, Trino/reporting, Grafana/Prometheus/health exporter and Kafka UI, while leaving core Commerce/Kafka active. Therefore the documented operating sequence is one heavy profile at a time; no Spark memory-limit increase is justified by this evidence.
