# M07 Unit 4 — partial returns and simulated refunds

Development checkpoint · 2026-10-24 · Not executed. Run after Stage 1 development and the consolidated automated pass.

## Services and configuration

1. Start the local profile with `devops/scripts/supersports up` and confirm Configuration, Orders, Fulfillment, Payment, PostgreSQL, Identity and Storefront are healthy.
2. Open the operator workspace at `http://localhost:3000/admin`; under **Returns policy**, confirm the default window is 30 days. Change it with the displayed expected revision and confirm a stale revision is rejected. Restore the intended value after the check.
3. Prepare an owned order, advance its synthetic shipment through `HANDED_OFF` and `IN_TRANSIT` to `DELIVERED`, and record the delivered timestamp and revision.

## Customer UI and API

1. Sign in as the order owner at `http://localhost:3000/orders`; the delivered order shows returnable quantities and a request-return action.
2. Request one unit from a multi-quantity line. Confirm the UI shows its `returnId`, pending/completed state and immutable refund total.
3. Request a second partial return with a separate idempotency key. Confirm aggregate returned quantity never exceeds the purchased quantity.
4. Repeat a request with the same key and identical body; confirm the original return operation is returned. Change the quantity under that key and confirm conflict.
5. Repeat as another customer and confirm the order and return ID are hidden with 404.
6. Advance a separate order past the configured return deadline. Confirm eligibility returns `RETURN_WINDOW_EXPIRED` and the POST does not create a return row.
7. Confirm the customer-facing order history reports delivered; returns do not change sellable stock before the separate inspection milestone.

## Read-only database checks

Use the existing per-service owner/read-only DBeaver connections. Do not cross-join service-owned tables.

```sql
-- Configuration DB
SELECT key, value, revision FROM configuration_setting WHERE key='returns.window-days';
SELECT setting_key, old_value, new_value, old_revision, new_revision, actor
FROM configuration_setting_audit WHERE setting_key='returns.window-days' ORDER BY id DESC LIMIT 5;

-- Orders DB
SELECT return_id, order_id, status, amount_minor, currency, policy_revision, window_days, delivered_at, fence
FROM return_request WHERE order_id='<synthetic-order-uuid>' ORDER BY created_at;
SELECT sku_id, count(*) AS units, sum(merchandise_refund_minor) AS merchandise_minor,
       sum(tax_refund_minor) AS tax_minor
FROM return_unit_allocation WHERE order_id='<synthetic-order-uuid>' GROUP BY sku_id ORDER BY sku_id;
SELECT event_type, event_version, aggregate_sequence, payload->'data' AS data
FROM order_outbox WHERE aggregate_id='<synthetic-order-uuid>' ORDER BY aggregate_sequence;

-- Payment DB
SELECT operation, amount_minor, currency, state, operation_key
FROM payment_operation WHERE order_id='<synthetic-order-uuid>' ORDER BY id;
```

For each order, the sum of its return allocations must not exceed line merchandise after discount plus captured tax, and Payment's cumulative refunds must remain at or below the one capture. Shipping is excluded from partial returns. Inventory must have no return restock movement yet; Unit 5 owns inspection and restock.

## Result record

- Date/time and commit:
- Synthetic order/return IDs:
- Service health and operator setting result:
- Customer eligibility and partial-return journey:
- Ownership/idempotency/concurrency result:
- Orders/Payment/Configuration database consistency:
- Inventory unchanged before inspection:
- Issues and notes:
- Owner acceptance: pending
