# Orders service

The Orders service owns customer-scoped checkout request claims, immutable order snapshots, checkout Saga state and the transactional outbox. It validates the customer realm and derives ownership only from the verified JWT subject.

Local verification uses the pinned Maven/JDK image through `./devops/scripts/supersports unit`. The service is built and deployed by the root Compose profile; its database is provisioned as `orders` with the `supersports_orders` role.

The customer checkout endpoint claims an idempotency key before external reads, snapshots the authenticated customer's saved Indian address, obtains active SKU facts from Catalog, an authoritative INR/USD quote from Pricing, and simulation settings from Configuration. It then stores the immutable order header and lines, initial Saga/step and `OrderAccepted` outbox row in one Orders database transaction. A matching retry returns the same order; another customer cannot read it. The fenced worker coordinates inventory, coupon, simulated payment and shipment scheduling.

M07 tracking work adds an owner-checked tracking endpoint that verifies the order in the Orders database before calling Fulfillment with the existing worker identity. Fulfillment outage is represented as unavailable tracking while owned order data remains accessible. Future post-purchase event mirroring remains gated on the versioned event contract and dual-version History consumer in M07 Unit 8. New tracking source awaits the consolidated Stage 1 verification pass.
