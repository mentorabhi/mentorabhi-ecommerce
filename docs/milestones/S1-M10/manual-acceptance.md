# S1-M10 manual acceptance — synthetic customer and order dataset

Use this checklist after the automated run. The dataset is persistent; do not delete it as part of routine acceptance.

## Services

- [ ] Start core plus streaming and optional analytics using `devops/scripts/supersports status` and `devops/scripts/supersports analytics-up`.
- [ ] Confirm Identity, Catalog, Pricing, Inventory, Customer, Orders, Kafka, Kafka Connect, Order History, Trino, and the Analytics API are healthy.
- [ ] Confirm storefront `http://localhost:3000` and Admin → Analytics are reachable.

## Storefront and customer profiles

- [ ] Browse Cricket and Football. Confirm new product photos render, variant attributes differ, each variation has its own SKU, and INR/USD prices are present.
- [ ] Sign in with one generated customer listed in the ignored local credential file. Verify its Indian address and order history show only that account's orders.
- [ ] Sign in with a second generated customer and confirm the first customer's orders are not visible.
- [ ] Confirm generated accounts use `.invalid` email addresses and no email was sent.

## Analytics UI

- [ ] Select INR and 365 days. Confirm nonzero GMV, order count, AOV, daily trend, and top products.
- [ ] Switch to USD and confirm only USD totals appear.
- [ ] Change to 7 and 30 days and confirm the report date range and counts change.
- [ ] Confirm the dashboard continues to label unavailable funnel, retention, coupon-attribution, and inventory-health metrics rather than implying they are measured.

## Database reconciliation (read-only)

- [ ] In DBeaver, use the local PostgreSQL connection from `docs/setup/database-access.md`.
- [ ] Query `catalog` through its owner/admin connection: count products and active SKUs for the fixture prefix; confirm exactly 10 product models and 100 SKUs.
- [ ] Query `inventory` through its owner/admin connection: confirm 100 fixture SKU balances, none negative, and stock movements carry the stable seed key.
- [ ] Query `customer` through its owner/admin connection: confirm 1,000 fixture profiles with Indian country code `IN`.
- [ ] Query `orders` through its owner/admin connection: count unique source references, orders, order lines, currencies, and minimum/maximum `occurredAt`; confirm the range is within the last 365 days and every order has one generated owner.
- [ ] Compare INR and USD confirmed-order totals with the matching Trino report query. Record the query window, seed ID, row counts, and reconciliation result.

## Result

- Date/time:
- Seed ID:
- Outcome:
- Notes:
