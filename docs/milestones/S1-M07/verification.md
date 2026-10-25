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

## Event compatibility development checkpoint

Added immutable `order-lifecycle-v2.schema.json`, an allowlisted Orders v2 writer entry point, strict History parsing for v1/v2 envelopes, v2 state handling in rebuild reconciliation, and version-selecting schema validation for replay/streaming fixtures. V1 schema and writer path remain unchanged. Test source covers v2 schema, privacy rejection, parser allowlist and reconciliation state, but no tests/build were executed under the user's development-first direction. No v2 event is emitted until cancellation/return flows are implemented.

## Unit 1 — Payment ledger bounds

Design/review before code: [`payment-ledger-design.md`](payment-ledger-design.md), [`payment-ledger-flow.mmd`](payment-ledger-flow.mmd). Migration preflight on the existing local Payment DB found 67 authorization rows and 54 capture rows, with no order having duplicate authorization/capture/void. Migration V2 applied successfully.

- Pinned Maven image, `mvn -B -ntp verify`: 10 tests passed (five simulator/idempotency/fence tests, five pure ledger-rule tests).
- Targeted live integration `SUPERSPORTS_INTEGRATION=1 SUPERSPORTS_PROJECT=supersports .venv/bin/python -m unittest discover -s devops/tests -p test_core_integration.py -k payment_ledger -v`: passed. Covered one capture, exact cumulative refunds, concurrent final-capacity refunds, cross-order key reuse (including simultaneous competing claims), currency mismatch and capture after void.
- Normal checkout regression (`-k checkout_creates_owner`): passed; existing worker still leaves one authorization and one capture and completes shipment scheduling.
- Payment service rebuilt/recreated and healthy; readiness returned UP.

Not full CI. Remaining M07 units, UI, final integration/recovery, owner manual acceptance and milestone completion remain open. No payment provider is connected.
# Development-first checkpoint — Unit 3 cancellation

Cancellation source and test cases are authored but unverified. Per the user's sequencing instruction, no build, test, or runtime checks have been run after the M06 checkpoint. The consolidated verification pass begins from M06 after development across all Stage 1 milestones is complete. Manual owner checks are in [cancellation-manual-checks.md](cancellation-manual-checks.md).

Partial returns and refunds are also authored but unverified. Unit test, real-stack integration test, Selenium journey, policy setting audit, and manual owner checks are written; no execution has started. See [returns-refunds-manual-checks.md](returns-refunds-manual-checks.md).

## Development-first checkpoint — Unit 5 inspection and restock

Inventory receipt registration and complete per-unit SELLABLE/DAMAGED/DISPUTED inspection are authored with operation identity, revision fencing, audit actor/reason and sellable-only restock movement. Orders retries registration after refund completion using a persisted lease state. Operator UI, OpenAPI contract, Java unit tests, real-stack integration assertions, Selenium fixture journey and a separate manual guide are present. No build, test, or runtime check has been executed for this checkpoint; all outcomes remain unverified until Stage 1 development is complete.

## Development-first checkpoint — Units 6–7 reviews and support

Added independent Reviews and Support Spring projects, database migrations/credentials, public/customer/operator API routes, minimal owner verification through Orders, pending moderation and audited decisions, owner-scoped tickets and idempotent messages, storefront customer/operator workflows, OpenAPI contracts, unit/integration/Selenium source and manual steps. New services are included in the core Compose profile. No build, test, or runtime check has been executed. Unit 8 source integration is recorded below.

## Development-first checkpoint — Unit 8 UI integration

Authored operator shipment lookup/progression and customer tracking timeline UI, fulfillment read contract, same-origin route, Selenium source and updated manual acceptance. Tracking remains a read through Orders to the Fulfillment owner API; no cross-service database projection or unsafely synthesized tracking event is introduced. M07 code is not verified. No test, build or service command was run for this checkpoint.


## Consolidated post-purchase acceptance — 2026-10-24

`SUPERSPORTS_POSTPURCHASE_LIVE=true .venv/bin/python -m unittest devops.tests.test_postpurchase_integration -v`: 3 passed in 65.746 seconds against the real local APIs/databases. Verified: cancellation survives a stopped/restarted Payment service, retry returns the same operation and exactly one refund, a handed-off shipment and cancellation have one winner, delivered review rejects another customer's order and a wrong product, moderation is private until publication and idempotent/audited, support rejects another owner and conflicting retries, operator reply is visible to the owner, Reviews/Support restart preserves data, and a customer reply reopens a resolved ticket.

Verified-review product binding regression failed first (`VerifiedReviewProductTest`); after returning the purchased product in the Orders proof and checking it in Reviews, Reviews and Orders Maven `verify` passed. Core CI's real partial-return/refund/inspection regression also passed as part of all 25 core integration cases. Browser acceptance remains separately recorded.

## Stage 1 post-purchase rerun — 2026-10-25

After the full demo dataset was loaded and all application services rebuilt, the live M07 suite was rerun:

`SUPERSPORTS_POSTPURCHASE_LIVE=true PYTHONPATH=devops/scripts .venv/bin/python -m unittest devops.tests.test_postpurchase_integration -v` — 3/3 passed in 57.960 seconds.

The three journeys passed cancellation ownership/idempotency during Payment-simulator outage and recovery; concurrent handoff/cancellation single-winner fencing; and delivered purchase product-bound review verification, moderation replay/conflict, support owner isolation, idempotent replies/status, and Reviews/Support restart persistence. Core integration separately passed partial-return/refund allocation, duplicate protection and return inspection. Selenium feature tests and owner-run manual checks are still pending; details/expected database outcomes are in the separate [manual acceptance](manual-acceptance.md) and unit guides.

## Consolidated UI and post-purchase regression — 2026-10-25

The full Selenium suite completed: 20 discovered journeys, 16 passed and 4 intentionally skipped outside their isolated Kafka-gap/Kafka-UI/Grafana profiles. The gap/outage storefront journeys and Kafka UI/Grafana browser checks were separately exercised and passed in their profile-specific runs. M07 customer/operator journeys covered ownership, cancellation, returns/refunds, inventory return inspection, shipment progression, review moderation, support, and customer history. `devops/scripts/supersports unit` also passed its repository-wide run; 34 live-only checks are intentionally skipped in unit mode. See the consolidated status record for command artifacts and exact suite counts.

M07 local automated acceptance is complete for exercised paths. The separate owner-facing UI/database checklist is still unchecked and must be run manually; no real payment or carrier integration is implied.
