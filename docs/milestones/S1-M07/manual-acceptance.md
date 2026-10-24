# S1-M07 manual acceptance — post-purchase lifecycle

Status: Development in progress. Payment ledger and Fulfillment/Orders tracking APIs are implemented in source. UI advancement, lifecycle mirror events, cancellation, returns, reviews and support await their implementation units. Per user direction, new automated execution resumes after all Stage 1 development is complete.

## Start and health

1. Run `./devops/scripts/supersports streaming-up` and `./devops/scripts/supersports status`.
2. Confirm Orders, Payment, Fulfillment, Inventory, Reviews, Support, Kafka, Connect, Order History, PostgreSQL, identity and storefront report healthy.
3. Open `http://localhost:3000` and `http://localhost:3000/admin`. Sign in using locally configured customer/operator accounts; passwords remain in ignored `.local` files.

## Customer UI

1. Sign in as a self-registered customer, complete a simulated purchase, and open Account → Orders.
2. Open the owned order's tracking view and confirm the simulator state, stable tracking ID, revision, estimated delivery and transition history. In the operator workspace, advance one milestone at a time using the displayed revision; verify the reason/actor audit and retry the same operation ID. UI controls are part of Unit 8 development.
3. Before handoff, request cancellation and confirm its final state and simulated refund/void summary. Repeat the request and verify effects are not duplicated.
4. For a delivered order, request a partial line return. Confirm a second request cannot exceed the purchased quantity.
5. Submit a review for the delivered line; confirm it remains pending and unpublished before moderation.
6. Create a Support ticket and reply; reload and confirm only this customer sees it.

## Operator UI

1. Advance shipment using synthetic milestones; confirm audit actor/reason.
2. Publish or reject a pending review; confirm the catalog exposes only published reviews.
3. Record accepted and rejected return inspection outcomes. Confirm only accepted units restock, once.
4. Reply to a Support ticket without impersonating the customer; confirm actor/reason audit.

## Read-only database checks

Use owner-scoped database accounts from ignored `devops/.local/bootstrap.env`; never use an application role to inspect another service's tables. Check Orders, Payment, Fulfillment, Inventory, Reviews and Support for consistent operation IDs, bounded refund totals, return quantities, restock decisions, moderation history, and ticket ownership. Add exact read-only SQL after schemas are implemented.

### Payment ledger unit (available now)

1. Run checkout through the storefront and confirm its Payment record shows one `AUTHORIZED` and one `CAPTURED` row.
2. Use the local payment status API from the integration suite or inspect the Payment database. Verify there is at most one authorization/capture per order, capture amount/currency equal authorization, and cumulative refunds stay at or below capture.
3. With the synthetic API scenarios in the integration test, verify a repeated capture, over-refund, cross-order operation-key reuse and capture-after-void receive conflict; two concurrent refunds cannot exceed the capture.
4. Query only the Payment database with its own read-only admin connection. Example: `SELECT operation, state, currency, amount_minor FROM payment_operation WHERE order_id = '<synthetic-order-uuid>' ORDER BY id;`

### Tracking and handoff unit (API source implemented; UI awaits Unit 8)

1. Use a customer token to call `GET /api/v1/orders/{owned-order-id}/tracking`; confirm it returns only the owned order's simulator state and that a different customer receives 404.
2. With the operator account, call `POST /api/v1/operator/shipments/{order-id}/transitions` using `{expectedRevision, operationId, targetState, reason}`. Advance `HANDED_OFF`, `IN_TRANSIT`, then `DELIVERED`, increasing the expected revision each time.
3. Retry an identical operation ID/request and confirm its original receipt. Reuse that ID with a changed reason or target and expect 409; use a stale revision and expect 409; try to skip a milestone and expect 409.
4. If Fulfillment is unavailable, the owned Orders tracking response reports `UNAVAILABLE` without disclosing another service's data. Read the transition audit only from the Fulfillment database owner connection.

The checks above have automated evidence; human execution is still pending. Never use real payment data.

## Result record

- Date/time and branch/commit:
- Customer journey result:
- Operator journey result:
- Service health result:
- Database consistency result:
- Issues and notes:
- Owner acceptance: pending
