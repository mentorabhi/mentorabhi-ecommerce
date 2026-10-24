# M07 Unit 3 — customer cancellation manual checks

Development checkpoint · 2026-10-24 · Not yet executed. Run after the Stage 1 development pass and automated checks.

## Prepare isolated data

1. Start the local core profile with the repo command `devops/scripts/supersports up`.
2. Confirm `orders`, `payment-simulator`, `inventory`, `fulfillment-simulator`, `postgres`, `identity`, and `storefront` are healthy in Docker Desktop or `devops/scripts/supersports status`.
3. Create a dedicated customer and place a low-value simulated order. Wait until the Orders page shows `FULFILLMENT_SCHEDULED`.
4. Do not advance that shipment to `HANDED_OFF`; the scenario requires the scheduled state.

## Customer UI

1. Open `http://localhost:3000/orders`, sign in as the order owner, and open the prepared order.
2. Confirm `Cancel order` appears only while the order and shipment remain eligible.
3. Select cancellation once. Confirm the page shows the asynchronous operation and finishes at `CANCELLED` / `completed`.
4. Reload the order and verify it remains cancelled. Confirm the button is absent.
5. In another synthetic order, advance the shipment to `HANDED_OFF` before opening the order. Confirm cancellation is unavailable.
6. Sign in as a different customer and request the first customer's order detail and cancellation operation through the UI/API. Confirm the result is 404 and no identifiers or details leak.

## API and service behavior

1. Check `GET /api/v1/orders/{orderId}/cancellation-eligibility` with the customer token. A settled scheduled shipment reports eligible. An in-progress, delivered, handed-off, or cancelled order reports ineligible.
2. POST `{"reasonCode":"CUSTOMER_REQUEST"}` to `/api/v1/orders/{orderId}/cancellations` with an `Idempotency-Key`. Confirm 202 and poll `/api/v1/orders/{orderId}/cancellations/{operationId}` to `COMPLETED`.
3. Repeat the same idempotency key and body; confirm it returns the same operation. Reuse the key for a different order and confirm conflict.
4. Race a shipment handoff against cancellation using a separate disposable order. Exactly one may win. If handoff wins, cancellation becomes `REJECTED` with `HANDOFF_WON`, with no refund or restock. If claim wins, handoff cannot proceed.
5. Stop one downstream service during a dedicated attempt. Confirm retry retains the operation identity and the customer sees its state; an unresolved downstream conflict is visible as `MANUAL_REVIEW`.

## Owner database checks

Use the corresponding local owner/read-only connections in DBeaver; do not join private service tables.

```sql
-- Orders DB: operation must complete and one v2 cancellation event must exist.
SELECT operation_id, order_id, status, current_step, fence, last_error_code
FROM post_purchase_operation WHERE order_id = '<synthetic-order-uuid>';
SELECT event_type, event_version, aggregate_sequence, payload->'data' AS data
FROM order_outbox WHERE aggregate_id = '<synthetic-order-uuid>' ORDER BY aggregate_sequence;

-- Payment DB: one refund, bounded by the capture.
SELECT operation, amount_minor, currency, state, operation_key
FROM payment_operation WHERE order_id = '<synthetic-order-uuid>' ORDER BY id;

-- Inventory DB: committed allocation reversed once with an append-only movement.
SELECT state, cancellation_operation_id FROM inventory_reservation WHERE order_id = '<synthetic-order-uuid>';
SELECT sku_id, delta, source, idempotency_key FROM stock_movement
WHERE source = 'cancellation' AND idempotency_key LIKE 'cancel:%' ORDER BY occurred_at;

-- Fulfillment DB: claim and finalize audit, with monotonic shipment revision.
SELECT state, revision, cancel_claim_operation_id, cancellation_operation_id
FROM shipment WHERE order_id = '<synthetic-order-uuid>';
SELECT action, previous_state, next_state, previous_revision, next_revision
FROM shipment_cancellation_audit WHERE order_id = '<synthetic-order-uuid>' ORDER BY created_at;
```

## Result record

- Date/time and commit:
- Synthetic order ID:
- Service health:
- Owner UI/API journey:
- Handoff race result:
- Orders/Payment/Inventory/Fulfillment database consistency:
- Issues and notes:
- Owner acceptance: pending
