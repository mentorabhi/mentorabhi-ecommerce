# S1-M08 analytics dashboard and metric definitions

## Where users see analytics

The built-in operator dashboard is at **Admin → Analytics** (`http://localhost:3000/admin`), served by the analytics API and curated Trino tables. It has INR/USD and 7/30/90/365-day period controls, commerce KPI cards, a daily merchandise-sales chart, top products, and a refund-by-reason report. Superset at `http://localhost:8095` is an optional local dashboard studio for ad hoc visualizations; the SQL source reports are in `data/pipelines/lakehouse/reports.sql`.

## Metric definitions

| Metric | Definition | Currency / caveat |
|---|---|---|
| Gross merchandise value (GMV) | Sum of immutable `OrderAccepted.data.subtotalMinor` for orders with an `OrderConfirmed` lifecycle event | Confirmed merchandise subtotal before discounts, tax and shipping |
| Confirmed order value | Sum of immutable `OrderAccepted.data.totalMinor` for orders with an `OrderConfirmed` lifecycle event | Confirmed orders only; includes quoted tax and shipping |
| Confirmed orders | Distinct accepted order aggregates with a later `OrderConfirmed` event | Excludes failed checkout and unconfirmed accepted orders |
| Average order value | Confirmed order value / confirmed order count | Same currency; zero when there are no confirmed orders |
| Net merchandise sales | GMV less confirmed order discounts | Does not subtract refunds; excludes tax and shipping |
| Units sold | Sum of purchased quantities on confirmed order lines | Uses purchase snapshots, not current catalog stock |
| Items per order | Units sold / confirmed order count | Zero when there are no confirmed orders |
| Discount rate | Confirmed order discounts / confirmed GMV | Selected period; zero when GMV is zero |
| Completed refunds | Sum of `OrderRefundCompleted.data.amountMinor` | Completed refund events only; a partial refund contributes only its amount |
| Net cash sales | Confirmed order value accepted in period minus refund amounts issued in period | Period activity measure, not a lifetime order cohort; refund can include allocated tax |
| Refund amount rate | Refund amount issued in period / order value accepted in period | Period activity ratio, not a lifetime order cohort; zero when denominator is zero |
| Discounts | Sum of accepted order-level discounts for confirmed orders | Historical discount snapshots, not current coupon configuration |
| Cancellation count | Distinct orders with `OrderCancelled` | Reported separately from refund amount |
| Return count | Distinct orders with `OrderReturnRequested` | A request count, not a count of inspected/restocked units |
| Daily merchandise sales | Confirmed GMV and order count grouped by order acceptance date | 7/30/90/365-day period; batch freshness follows the last successful Spark run |
| Top products | Confirmed order line units and line sales grouped by product snapshot in selected period | Product title is the title captured at purchase, not current catalog title |

Never add unlike currencies. Conversion, sessions, cart abandonment, visitor counts, customer lifetime value, repeat-customer rate, coupon attribution, inventory on-hand, sell-through and stockout rates remain unavailable until their source events/owner APIs and privacy definitions are approved. Stock availability remains in the Inventory operator view and is not inferred from historical orders. See [standard metrics design](standard-commerce-metrics-design.md) and its [review](standard-commerce-metrics-review.md).

## Dashboard and report list

1. **Commerce overview:** GMV, net merchandise sales, confirmed order count, AOV, units/items per order, discounts/discount rate, completed refunds/refund amount rate, net cash sales, cancellations and return requests; currency and period selectors.
2. **Sales trend:** selected-period GMV and order count by day; use Trino `order_sales`.
3. **Product performance:** top products by units and confirmed line sales; use `order_lines` joined to confirmed `order_sales` for the same period.
4. **Returns and refunds:** completed refund amount/events by day and reason plus separate cancellation and return-request counts for the selected period.
5. **Data quality/reconciliation:** source coordinates, quarantined rows, latest event timestamp, and per-currency aggregate comparison to owner records; operator-only verification, not a customer-facing report.

The dashboard is a rebuildable read model. It is not an accounting ledger or an authority for payment/order state. Period sales follow order acceptance time; refund/cancellation/return counts follow their activity time. The latest event label is event time, not proof of ingestion freshness. All figures remain unverified until the consolidated Stage 1 test pass.
