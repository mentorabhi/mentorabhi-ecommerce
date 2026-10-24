# S1-M08 manual acceptance — graph and reporting

Status: Implementation source is present; all runtime and end-user checks are pending the consolidated Stage 1 verification pass.

## Services and UI

1. Start core services first, then run `devops/scripts/supersports analytics-up`. Confirm Trino and report API health. Open the built-in operator dashboard at `http://localhost:3000/admin` → Analytics. Start optional Superset with `devops/scripts/supersports dashboard-studio-up`; open `http://localhost:8095`. Start the separate graph profile with `devops/scripts/supersports graph-up`; open graph API at `http://localhost:8094/docs` and Neo4j Browser at `http://localhost:7474`.
2. In the operator dashboard, switch INR/USD and confirm each report stays within one currency. Check GMV, net merchandise sales, confirmed orders, AOV, units, discounts, refunds, net cash sales, cancellation/return counts, daily trend, top products, and refund reasons.
3. Select 7, 30, 90, and 365 days. Confirm the period label and summary, trend, product, and refund reports update together. Refresh and inspect the latest event timestamp.
4. Confirm GMV excludes discounts, tax and shipping; net merchandise sales subtracts discounts; AOV uses confirmed total including tax/shipping; units and items/order match confirmed purchase lines. Refund issue dates drive the refund period, and refund values can include allocated tax.
5. Confirm the dashboard explains that sessions, conversion, cart abandonment, coupon attribution, and inventory metrics have no source data and are not estimated.
6. Run `devops/scripts/supersports analytics-run` to replay Kafka into Iceberg. Repeat it and verify row counts and totals do not increase for duplicate source events.
7. In Superset, sign in with local `admin` / `admin`; add the Trino database URL `trino://supersports-reports@trino:8080/lakehouse/supersports`, use curated tables and `data/pipelines/lakehouse/reports.sql`, then create or inspect overview/trend/product/refund charts. The first-party dashboard works without Superset.
8. Open graph API docs and request related products; confirm query depth and result limits reject out-of-range values. Create a synthetic confirmed order and check it appears after Kafka delivery and batch ingestion.

## Database and reconciliation

1. Confirm Neo4j node/relationship counts against the deterministic fixture. Redelivery must not create duplicate order/product edges.
2. Query Iceberg raw/curated tables through Trino for source event IDs and partition/offset lineage. Check quarantine coordinates and replay idempotency.
3. Compare period GMV, discounts, confirmed order totals/count, quantities, refunds, cancellations, and return requests with equivalent Trino SQL and Orders/Payment owner records. Confirm cancellation and partial return values are represented once, grouped by activity time, and separated by currency.
4. Check PostgreSQL catalog database connectivity and Iceberg table metadata; confirm local warehouse files exist and Trino sees them.
5. Confirm no customer key, address, phone, customer name, coupon code, review text, or support content is present in graph/curated tables. Confirm only the allowlisted order snapshot fields are retained.

## Result record

Record date, commit, profiles, service health, data snapshot/freshness, report queries, per-currency reconciliation, graph counts and discrepancies. Keep measured values separate from proposed targets.
