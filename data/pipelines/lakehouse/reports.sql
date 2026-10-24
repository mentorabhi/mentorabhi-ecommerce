-- Saved report queries. Always group/filter by currency; no currency conversion is implied.
-- Storewide, lifetime confirmed commerce overview. Dashboard APIs add a selected-period predicate.
SELECT currency, COUNT_IF(confirmed) AS confirmed_orders,
       SUM(IF(confirmed,subtotalMinor,0)) AS gross_merchandise_value_minor,
       SUM(IF(confirmed,totalMinor,0)) AS confirmed_order_value_minor,
       SUM(IF(confirmed,discountMinor,0)) AS confirmed_discounts_minor,
       SUM(IF(confirmed,totalMinor,0)) / NULLIF(COUNT_IF(confirmed),0) AS average_order_value_minor
FROM lakehouse.supersports.order_sales GROUP BY currency;

-- Daily selected-period GMV and order totals. Bind one currency and a 7–365 day range.
SELECT currency,CAST(occurredAt AS DATE) AS sales_day,COUNT(*) AS confirmed_orders,
       SUM(subtotalMinor) AS gross_merchandise_value_minor,
       SUM(totalMinor) AS confirmed_order_value_minor,
       SUM(discountMinor) AS discounts_minor
FROM lakehouse.supersports.order_sales
WHERE confirmed AND currency='INR'
  AND occurredAt >= current_timestamp - INTERVAL '30' DAY
GROUP BY currency,CAST(occurredAt AS DATE) ORDER BY sales_day;

-- Confirmed item volume and product performance for a selected period.
SELECT l.currency,l.productId,l.productTitle,SUM(l.quantity) AS units_sold,
       SUM(l.lineTotalMinor) AS confirmed_line_sales_minor
FROM lakehouse.supersports.order_lines l
JOIN lakehouse.supersports.order_sales s USING (aggregateId)
WHERE s.confirmed AND l.currency='INR'
  AND s.occurredAt >= current_timestamp - INTERVAL '30' DAY
GROUP BY l.currency,l.productId,l.productTitle;

-- Completed refunds stay separate from confirmed order facts.
SELECT currency, reasonCode, CAST(occurredAt AS DATE) AS refund_day,
       COUNT(*) AS refund_events, SUM(amountMinor) AS refunded_minor
FROM lakehouse.supersports.order_refunds GROUP BY currency,reasonCode,CAST(occurredAt AS DATE);

-- Top products from the purchase snapshot, only for confirmed orders.
SELECT l.currency,l.productId,l.productTitle,SUM(l.quantity) AS units_sold,
       SUM(l.lineTotalMinor) AS confirmed_line_sales_minor
FROM lakehouse.supersports.order_lines l
JOIN lakehouse.supersports.order_sales s USING (aggregateId)
WHERE s.confirmed GROUP BY l.currency,l.productId,l.productTitle;

-- Cancellation and return-request counts are counts of distinct affected orders.
SELECT s.currency,
       COUNT(DISTINCT IF(r.eventType='OrderCancelled',r.aggregateId,NULL)) AS cancelled_orders,
       COUNT(DISTINCT IF(r.eventType='OrderReturnRequested',r.aggregateId,NULL)) AS return_request_orders
FROM lakehouse.supersports.raw_lifecycle r
JOIN lakehouse.supersports.order_sales s USING (aggregateId)
GROUP BY s.currency;
