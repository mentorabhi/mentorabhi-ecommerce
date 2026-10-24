# M07 Units 6–7 — manual reviews and support checks

Development checklist dated 2026-10-24. Do not treat these steps as executed; testing remains deferred until Stage 1 development is complete.

## Service and storefront checks

1. Start the full local commerce and streaming profiles. Confirm Reviews, Support, Orders, Fulfillment, Storefront and identity report healthy.
2. Sign in as a customer, place a simulated order, advance its shipment through the operator simulator to DELIVERED, then open the order in the customer storefront.
3. Submit a review for one purchased SKU. Confirm it is marked pending moderation and is not publicly visible.
4. In `/admin`, open Reviews, publish the review, and confirm its title/body and rating appear in the product's public review feed. Reject a second synthetic review and confirm it remains private.
5. Open Customer Support, create a ticket with no linked order, and confirm it appears in the customer's own list. Reply as the customer, then respond from the operator queue and confirm both messages and actor audiences.
6. Create another ticket linked to an owned order. Try a different customer's order and confirm the request is rejected with no ticket persisted.

## Database and ownership checks

1. In the `reviews` database, inspect `product_review` and `review_moderation_audit`. Confirm new rows begin PENDING, moderation records actor/reason/state, uniqueness prevents a second review for the same customer/order/SKU, and public rows are PUBLISHED only.
2. In the `support` database, inspect `support_ticket`, `support_message` and `support_audit`. Confirm ownership comes from the verified customer subject, replies retain CUSTOMER/OPERATOR audience, status transitions have actor/reason audit, and identical message operation retries do not duplicate rows.
3. Confirm neither database stores bearer tokens. Confirm neither support/review body appears in the Orders outbox or Order History projection.
4. Confirm customer A receives 404 when requesting customer B's ticket/review resources; customer tokens cannot access operator routes; operator tokens cannot access customer routes.

## Result record

Record commit, profile, service readiness, customer/order/review/ticket IDs, moderation and reply results, DB query outcomes and discrepancies. Do not mark a check passed until it has been run.
