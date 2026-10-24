# S1-M08 analytics dashboard and metric definitions

## Where users see analytics

The built-in operator dashboard is at **Admin → Analytics** (`http://localhost:3000/admin`), served by the analytics API and curated Trino tables. It has INR/USD switching, five KPI cards, a 30-day daily-sales chart, top products, and a refund-by-reason report. Superset at `http://localhost:8095` is an optional local dashboard studio for ad hoc visualizations; the SQL source reports are in `data/pipelines/lakehouse/reports.sql`.

## Metric definitions

| Metric | Definition | Currency / caveat |
|---|---|---|
| Confirmed sales | Sum of immutable `OrderAccepted.data.totalMinor` for orders with an `OrderConfirmed` lifecycle event | Confirmed orders only; includes the captured order total with tax/shipping as quoted |
| Confirmed orders | Distinct accepted order aggregates with a later `OrderConfirmed` event | Excludes failed checkout and unconfirmed accepted orders |
| Average order value | Confirmed sales / confirmed order count | Same currency; zero when there are no confirmed orders |
| Completed refunds | Sum of `OrderRefundCompleted.data.amountMinor` | Completed refund events only; a partial refund contributes only its amount |
| Net sales | Confirmed sales minus completed refund amounts | Refunds are subtracted once; cancellations are not separately subtracted again |
| Discounts | Sum of accepted order-level discounts for confirmed orders | Historical discount snapshots, not current coupon configuration |
| Cancellation count | Distinct orders with `OrderCancelled` | Reported separately from refund amount |
| Return count | Distinct orders with `OrderReturnRequested` | A request count, not a count of inspected/restocked units |
| Daily confirmed sales | Confirmed order totals grouped by order acceptance date | One currency at a time; batch freshness follows the last successful Spark run |
| Top products | Confirmed order line units and line sales grouped by product snapshot | Product title is the title captured at purchase, not current catalog title |

Never add unlike currencies. Conversion, cart abandonment, visitor counts, customer lifetime value, and cohort retention are intentionally absent until their source events and privacy definitions are approved. Stock availability remains in the Inventory operator view and is not inferred from historical orders.

## Dashboard and report list

1. **Commerce overview:** confirmed sales, AOV, refunds, net sales, discounts, cancellations, return requests; currency selector and refresh/freshness note.
2. **Sales trend:** 30-day confirmed sales and order count by day; use Trino `order_sales`.
3. **Product performance:** top products by units and confirmed line sales; use `order_lines` joined to confirmed `order_sales`.
4. **Returns and refunds:** completed refund amount/events by day and reason plus separate cancellation and return-request counts.
5. **Data quality/reconciliation:** source coordinates, quarantined rows, latest event timestamp, and per-currency aggregate comparison to owner records; operator-only verification, not a customer-facing report.

The dashboard is a rebuildable read model. It is not an accounting ledger or an authority for payment/order state.
