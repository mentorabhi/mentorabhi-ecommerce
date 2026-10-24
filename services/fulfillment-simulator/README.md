# Fulfillment Simulator

Local idempotent shipment scheduling with synthetic `SS-...` tracking IDs. It stores shipments in its own PostgreSQL database and never calls a carrier. Calls require the checkout worker identity and fulfillment scope. Contract: `contracts/fulfillment-simulator/openapi.yaml`.

Post-purchase development adds revisioned `HANDED_OFF → IN_TRANSIT → DELIVERED` transitions, expected-revision checks, operation-ID replay/conflict, deterministic local ETA and append-only operator/reason audit. Customer tracking stays behind the owner-verified Orders API. New tracking source awaits the consolidated Stage 1 verification pass.

Build and test with `./devops/scripts/supersports unit`; run as part of the full `./devops/scripts/supersports up` profile.
