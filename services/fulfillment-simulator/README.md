# Fulfillment Simulator

Local idempotent shipment scheduling with synthetic `SS-...` tracking IDs. It stores shipments in its own PostgreSQL database and never calls a carrier. Calls require the checkout worker identity and fulfillment scope. Contract: `contracts/fulfillment-simulator/openapi.yaml`.

Build and test with `./devops/scripts/supersports unit`; run as part of the full `./devops/scripts/supersports up` profile.
