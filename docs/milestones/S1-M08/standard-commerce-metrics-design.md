# S1-M08 standard commerce metrics — design

Revision 1 · 2026-10-24 · Design first

## Goal

Give store operators a practical, time-filterable commerce dashboard and saved reports using only the published order lifecycle events already owned by the analytics projection. Make the meaning of each money metric explicit and preserve currency boundaries.

## Measures and definitions

All selected-period order measures use `OrderAccepted.occurredAt` for orders that also have `OrderConfirmed`. Refund and lifecycle activity measures use their own event timestamps. Results are grouped by the selected currency; no exchange rate or mixed-currency total is introduced.

| Measure | Definition |
|---|---|
| Confirmed orders | Distinct accepted orders with a later `OrderConfirmed`, accepted during the selected period |
| Gross merchandise value (GMV) | Sum of confirmed order `subtotalMinor` before order discount, tax and shipping |
| Promotion discounts | Sum of confirmed order `discountMinor` |
| Net merchandise sales | GMV less promotion discounts; excludes tax and shipping, and is not reduced by refunds |
| Confirmed order value | Sum of confirmed `totalMinor`, including quoted tax and shipping |
| Average order value (AOV) | Confirmed order value divided by confirmed orders |
| Units sold | Sum of quantities on confirmed order lines accepted in the period |
| Items per order | Units sold divided by confirmed orders |
| Completed refunds | Sum of `OrderRefundCompleted.amountMinor` events during the period; refund amount can include allocated tax |
| Net cash sales | Confirmed order value accepted in the period less completed refunds issued in the period; this is a period activity measure, not an order-cohort balance |
| Cancellation / return activity | Distinct order count of cancellation and return-request events occurring in the period; shown separately |
| Refund rate | Refund event amount divided by confirmed order value in the selected period; shown only when denominator is nonzero and identified as event-period activity |

## Reports and controls

- Commerce overview cards for GMV, net merchandise sales, confirmed orders, AOV, units sold, discounts, completed refunds, net cash sales, cancellations, and return requests.
- Discount rate is discounts divided by GMV; refund amount rate is refund amount issued in the period divided by order value accepted in the period. Both are period activity ratios, not cohort measures.
- Sales and order-count trend by day, with 7, 30, 90, and 365-day period selection.
- Product performance by units and confirmed line sales, scoped to accepted orders in the same period.
- Refund detail by day and reason code for the selected period.
- Currency controls remain INR/USD, consistent with currently supported price books.
- A freshness label reports the latest projected lifecycle event timestamp when available.

## Data and privacy

Continue to consume the public lifecycle topic and read only curated Iceberg tables. Do not add customer identifiers, addresses, payment details, or coupon codes. Do not read service databases. No new event or schema is needed for this increment.

Visitor conversion, sessions, cart abandonment, new/repeat customer counts, coupon attribution, inventory on-hand, sell-through, and stockout rates require source events or owner APIs that are not currently projected. They remain explicitly unavailable until those sources are designed and reviewed.

## Failure and limits

The report API validates currency, range, and result limits. Reports can return an explicit unavailable response while Trino/tables are not ready. Report freshness is bounded by the last successful batch ingestion; it is not a real-time financial ledger. Data remains rebuildable and subject to M08 reconciliation.

## Acceptance evidence to add

- Unit coverage for parameter bounds, selected-period query parameters, currency isolation, and empty denominators.
- Selenium coverage for period and currency controls, metric cards, trend, product and refund reports, and unavailable state.
- Manual guide checks for running profiles, database/table presence, period comparisons, INR/USD separation, and operator-visible limitations.

All build, test, and runtime checks remain deferred to the user's consolidated Stage 1 verification pass.
