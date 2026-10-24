# S1-M07 verification record

2026-10-24 · Implementation units are recorded independently; M07 remains incomplete until all post-purchase journeys are delivered.

## Unit 1 — Payment ledger bounds

Design/review before code: [`payment-ledger-design.md`](payment-ledger-design.md), [`payment-ledger-flow.mmd`](payment-ledger-flow.mmd). Migration preflight on the existing local Payment DB found 67 authorization rows and 54 capture rows, with no order having duplicate authorization/capture/void. Migration V2 applied successfully.

- Pinned Maven image, `mvn -B -ntp verify`: 10 tests passed (five simulator/idempotency/fence tests, five pure ledger-rule tests).
- Targeted live integration `SUPERSPORTS_INTEGRATION=1 SUPERSPORTS_PROJECT=supersports .venv/bin/python -m unittest discover -s devops/tests -p test_core_integration.py -k payment_ledger -v`: passed. Covered one capture, exact cumulative refunds, concurrent final-capacity refunds, cross-order key reuse (including simultaneous competing claims), currency mismatch and capture after void.
- Normal checkout regression (`-k checkout_creates_owner`): passed; existing worker still leaves one authorization and one capture and completes shipment scheduling.
- Payment service rebuilt/recreated and healthy; readiness returned UP.

Not full CI. Remaining M07 units, UI, final integration/recovery, owner manual acceptance and milestone completion remain open. No payment provider is connected.
