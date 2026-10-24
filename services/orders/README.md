# Orders service

The Orders service owns customer-scoped checkout request claims, immutable order snapshots, checkout Saga state and the transactional outbox. It validates the customer realm and derives ownership only from the verified JWT subject.

Local verification uses the pinned Maven/JDK image through `./devops/scripts/supersports unit`. The service is built and deployed by the root Compose profile; its database is provisioned as `orders` with the `supersports_orders` role.

The customer checkout endpoint claims an idempotency key before external reads, snapshots the authenticated customer's saved Indian address, obtains active SKU facts from Catalog, an authoritative INR/USD quote from Pricing, and simulation settings from Configuration. It then stores the immutable order header and lines, initial Saga/step and `OrderAccepted` outbox row in one Orders database transaction. A matching retry returns the same order; another customer cannot read it. Missing addresses and deterministic validation errors are rejected before order creation. The request currently remains `PENDING_PAYMENT`: inventory reservation, coupon hold, simulated payment, fulfillment and worker recovery are the remaining M05 implementation work.
