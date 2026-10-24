# Payment Simulator

Local deterministic payment lifecycle simulator. It stores authorization, capture, void and refund operations in its own PostgreSQL database. It accepts no card or bank data and connects to no payment provider. Calls require the checkout worker identity and an operation-specific scope. A monotonic order fence and stable operation key reject stale or conflicting retries.

Build and test with `./devops/scripts/supersports unit`; run as part of the full `./devops/scripts/supersports up` profile. Contract: `contracts/payment-simulator/openapi.yaml`.
