# S1-M07 verification record

2026-10-24 · Implementation units are recorded independently; M07 remains incomplete until all post-purchase journeys are delivered.

## Unit 2 development checkpoint — tracking and handoff

Implemented in source, with execution intentionally deferred by the user until Stage 1 development is complete:

- Fulfillment migration adds shipment revision, deterministic estimated-delivery timestamp, state/revision constraints and append-only transition audit keyed by globally unique operation UUID.
- Fulfillment operator API accepts a verified `supersports-api` token and requires expected revision, operation UUID, sequential target and bounded reason. It serializes concurrent operation reuse with a PostgreSQL advisory transaction lock and row lock; exact replay returns the recorded receipt, changed payload/order conflicts, stale revision and invalid transition return conflict.
- Fulfillment's existing checkout-only schedule/status API remains scoped to the exact checkout worker audience/client and schedule/status scopes.
- Orders now offers `GET /api/v1/orders/{orderId}/tracking`; it first checks order ownership using only its own database, then reads the narrow simulator API with the worker identity. A dependency outage is represented as `UNAVAILABLE`.
- Added the local transition-state unit test and updated both OpenAPI contracts. UI controls and lifecycle event mirroring remain Unit 8 work, after the post-purchase event version and dual-version History changes.

No build, unit test, integration test or UI test was run for this checkpoint, per the current development-first instruction. Review and manual steps are in [`tracking-handoff-review.md`](tracking-handoff-review.md) and [`manual-acceptance.md`](manual-acceptance.md). Do not treat the implementation as verified yet.

## Unit 1 — Payment ledger bounds

Design/review before code: [`payment-ledger-design.md`](payment-ledger-design.md), [`payment-ledger-flow.mmd`](payment-ledger-flow.mmd). Migration preflight on the existing local Payment DB found 67 authorization rows and 54 capture rows, with no order having duplicate authorization/capture/void. Migration V2 applied successfully.

- Pinned Maven image, `mvn -B -ntp verify`: 10 tests passed (five simulator/idempotency/fence tests, five pure ledger-rule tests).
- Targeted live integration `SUPERSPORTS_INTEGRATION=1 SUPERSPORTS_PROJECT=supersports .venv/bin/python -m unittest discover -s devops/tests -p test_core_integration.py -k payment_ledger -v`: passed. Covered one capture, exact cumulative refunds, concurrent final-capacity refunds, cross-order key reuse (including simultaneous competing claims), currency mismatch and capture after void.
- Normal checkout regression (`-k checkout_creates_owner`): passed; existing worker still leaves one authorization and one capture and completes shipment scheduling.
- Payment service rebuilt/recreated and healthy; readiness returned UP.

Not full CI. Remaining M07 units, UI, final integration/recovery, owner manual acceptance and milestone completion remain open. No payment provider is connected.
