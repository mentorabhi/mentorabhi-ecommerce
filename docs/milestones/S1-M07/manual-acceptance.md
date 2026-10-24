# S1-M07 manual acceptance — post-purchase lifecycle

Status: In progress. The Payment-ledger section below is executable now; remaining post-purchase sections await their service/API implementation.

## Start and health

1. Run `./devops/scripts/supersports streaming-up` and `./devops/scripts/supersports status`.
2. Confirm Orders, Payment, Fulfillment, Inventory, Reviews, Support, Kafka, Connect, Order History, PostgreSQL, identity and storefront report healthy.
3. Open `http://localhost:3000` and `http://localhost:3000/admin`. Sign in using locally configured customer/operator accounts; passwords remain in ignored `.local` files.

## Customer UI

1. Sign in as a self-registered customer, complete a simulated purchase, and open Account → Orders.
2. Advance the shipment simulator through transit and delivery; refresh the owned order and confirm tracking state changes.
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

The checks above have automated evidence; human execution is still pending. Never use real payment data.

## Result record

- Date/time and branch/commit:
- Customer journey result:
- Operator journey result:
- Service health result:
- Database consistency result:
- Issues and notes:
- Owner acceptance: pending
