# Orders service

The Orders service owns customer-scoped checkout request claims, immutable order snapshots, checkout Saga state and the transactional outbox. It validates the customer realm and derives ownership only from the verified JWT subject.

Local verification uses the pinned Maven/JDK image through `./devops/scripts/supersports unit`. The service is built and deployed by the root Compose profile; its database is provisioned as `orders` with the `supersports_orders` role.

The customer checkout endpoint claims an idempotency key before external reads, snapshots the authenticated customer's saved Indian address, obtains active SKU facts from Catalog, an authoritative INR/USD quote from Pricing, and simulation settings from Configuration. It then stores the immutable order header and lines, initial Saga/step and `OrderAccepted` outbox row in one Orders database transaction. A matching retry returns the same order; another customer cannot read it. The fenced worker coordinates inventory, coupon, simulated payment and shipment scheduling.

M07 adds owner-checked tracking, cancellation, and partial-return APIs. Cancellation is a persisted fenced workflow that claims shipment before simulated refund/restock and emits `OrderCancelled` v2 on completion. Return claims use Fulfillment delivery facts and a revisioned return-window setting, reserve immutable unit-level merchandise/tax allocation, then serialize idempotent Payment refunds; Inventory remains untouched until inspection. Allowlisted v2 return/refund events are consumed by the dual-version History source. These changes are development checkpoints only and await the consolidated Stage 1 verification pass.
