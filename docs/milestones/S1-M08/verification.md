# S1-M08 verification record

Revision 1 · 2026-10-25 · First full-dataset runtime pass; the duplicate-ingestion and graph-browser checks remain in progress.

## Environment and commands

- ARM64 Mac, 16 GB host, Docker allocation 7.75 GiB; Python 3.14.7 via repository `.venv`.
- Core Commerce and Kafka streaming profiles were active. Spark uses `local[2]`, a 1 GiB driver heap and a 1.5 GiB Compose cap. Trino uses a 1 GiB cap. Graph and Spark jobs are opt-in and are not run concurrently with each other.
- `devops/scripts/supersports analytics-up` initially exposed two Trino config errors (missing JDBC driver and a local filesystem root that doubled `/warehouse`); the config was corrected to `org.postgresql.Driver` and `local.location=/` and Trino then reached healthy state.
- `devops/scripts/supersports analytics-run` completed successfully against 35,460 seeded lifecycle events. A second run after the full synthetic dataset was loaded also exited zero; elapsed time observed from container timestamps was about 147 seconds. A further unchanged-data replay is still required to compare counts before/after.

## Live read evidence

After Trino had restarted with `local.location=/`, the following storefront-proxied report requests returned HTTP 200: 365-day INR summary, 365-day USD summary, 365-day INR daily sales, top five INR products and INR refunds.

Observed report values for the 365-day window at 2026-10-25 00:21 UTC:

| Currency | Confirmed orders | GMV (minor units) | Order value (minor units) | Discount (minor units) | Units |
|---|---:|---:|---:|---:|---:|
| INR | 15,982 | 13,822,004,000 | 16,468,186,520 | 0 | 46,560 |
| USD | 1,759 | 19,261,781 | 23,078,898 | 0 | 5,179 |

The range includes existing fixture/test commerce alongside the M10 dataset; compare the `demo-20261024-*` subset using its source registry and owner-database audit rather than assuming these are the demo-only totals. No refunds or return requests were present in this synthetic fixture snapshot. The first top-products request returned 503 because the join left `discountMinor` ambiguous; the query now qualifies line columns and its focused unit regression and live request pass.

## Automated checks

- `PYTHONPATH=services/analytics-api .venv/bin/python -m unittest discover -s services/analytics-api/tests -v`: 6 passed, including top-products column qualification.
- `GRAPH_DB_PASSWORD=unit-test-only PYTHONPATH=services/relationship-graph:contracts .venv/bin/python -m unittest discover -s services/relationship-graph/tests -v`: 2 passed.
- The UI Selenium analytics journey and Trino reconciliation, unchanged replay counts, full Graph projection and browser queries are recorded below after execution; they are not inferred from API health.

## Reconciliation and limits

Reconcile the M10 source-registry subset from [M10 verification](../S1-M10/verification.md) against Order owner rows and the accepted/confirmed public event data in Iceberg. Then compare all-time/event counts separately from the rolling 365-day report window. Retained invalid Kafka coordinates are quarantined by source coordinate; no customer-identifying fields are included. Manual owner checks remain in [manual acceptance](manual-acceptance.md).

## Final reconciliation and browser rerun — 2026-10-25 02:50 UTC

A parser defect was found when Java emitted valid ISO-8601 timestamps with 7–9 fractional digits. Python's `datetime.fromisoformat` rejected these events, causing valid events to be quarantined. The shared contract now truncates fractional precision only for timestamp validation; it preserves the original payload/timestamp. A nanosecond timestamp regression covers both `Z` and `+00:00` forms.

The Spark batch now rebuilds the quarantine Iceberg projection from the current replay, so previously misclassified valid coordinates are removed while currently invalid source coordinates remain represented. This uses the supported Spark/Iceberg path and avoids an unsupported Trino mutation. The final batch and a second idempotency replay both exited zero.

Final all-time Iceberg reconciliation:

| Projection | Rows / values |
|---|---:|
| Raw lifecycle events | 35,973 |
| Quarantined invalid coordinates | 29 |
| Order sales | 17,896 |
| Confirmed order sales | 17,863 |
| Total accepted order value, INR minor units | 16,533,201,681 |
| Total accepted order value, USD minor units | 23,078,898 |

Event-type rows: OrderAccepted 17,896; OrderConfirmed 17,863; OrderCancelled 4; OrderCheckoutExpired 10; OrderPaymentDeclined 23; OrderRefundCompleted 22; OrderReturnRequested 22; FulfillmentScheduled 133. The event table retains raw lifecycle events and is not expected to contain only valid analytics order sales. Replaying unchanged input preserved projection counts.

Analytics summary, daily-sales, top-products and refund report routes returned HTTP 200 for selected INR/USD windows. Analytics Selenium passed 2/2 after the final replay. The complete relationship graph rebuild reached Kafka high-water marks on all three partitions and projected 17,896 order nodes; graph product recommendations returned nine related products without returning the source product, and depth 3 was rejected with HTTP 422. The graph browser journey also passed separately.

On the 16 GB ARM64 host, Spark's controlled batch exited zero with `OOMKilled=false` when optional graph, Trino/report, and observability profiles were stopped during the heavy job. Bring-up order is recorded in the operational scripts; this is a measured single run, not a general concurrency or peak-capacity guarantee. Human Trino/database/UI manual checks remain pending in [manual acceptance](manual-acceptance.md).
