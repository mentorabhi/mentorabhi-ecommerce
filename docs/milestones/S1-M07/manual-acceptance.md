# S1-M07 manual acceptance — post-purchase lifecycle

Status: Not executable until implementation. Update commands and queries to match delivered services before asking the owner to run this checklist.

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

## Result record

- Date/time and branch/commit:
- Customer journey result:
- Operator journey result:
- Service health result:
- Database consistency result:
- Issues and notes:
- Owner acceptance: pending
