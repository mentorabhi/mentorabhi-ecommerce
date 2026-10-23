# Verification and regression strategy
Revision 1 · 2026-10-23.

## Required per feature
Unit tests cover each feature's domain behavior, validation, boundaries and failure paths. Use a controllable clock and deterministic seeds.
Integration tests use real local containerized dependencies for persistence, migrations, locking, messaging and adapters.
Contract tests validate public API/event/tool schema compatibility. Regression suites retain previously passing acceptance scenarios.
E2E tests exercise customer/admin journeys against running services, with mobile/keyboard checks for frontend changes. Test data is synthetic and isolated.
Major features/milestones require documented commands, environment, exact versions, dataset, results and known limitations. A green unit suite does not substitute for integration/regression execution.

## Risk-driven suites
Money/coupons: rounding, currency precision, discount allocation, concurrent limit consumption, expired quote/coupon, partial refunds.
Stock: final-unit competition, reservation expiry, retries, duplicate stock movements, return inspection.
Saga: restart at each participant boundary, timeout with unknown payment outcome, duplicate callback, failed compensation and reconciliation.
Events/data: duplicate/out-of-order events, schema evolution, poison messages, replay/rebuild, late facts and financial reconciliation.
Configuration: role checks, secret redaction, endpoint allowlist/redirect rejection, revision conflicts, validation failure, activation rollback, deployment-required pending states.
Nova: groundedness/retrieval/task success, tool argument validation, approval replay/expiry, injection, isolation, model outage, context limits, forgetting/cache invalidation.
Security: owner/role enforcement, authentication expiry, mass assignment, exposed local dependencies and secret leaks.

## Test locations and execution ownership
services/<name>/src/test for Java; services/nova/tests for Python; data/pipelines/tests for data; apps/storefront tests for UI; contracts/tests for schema compatibility.
Cross-service integration/E2E orchestration and local CI scripts live in devops/tests and devops/scripts. Tests may be collocated with code; infrastructure belongs in devops.
S1-M02 selects actual build tools and commands, adds a local all-checks entry point and verifies it from a clean checkout. No fictional commands are documented as executable today.

## S1-M01 verification
Documentation-only checks: local Markdown links resolve, requirements IDs map to acceptance examples and milestones, current editable diagram JSON loads, SVG parses, all original diagram pairs remain, no runtime/test result is invented.
Repository checks after foundation: .gitignore excludes representative secret/build/local-state paths while preserving source/env templates; git diff whitespace check.
Unit/integration/E2E/load: not applicable to this documentation-only milestone; not executed. Test suites become required with the first runnable feature.

## Proposed targets and recovery
Critical invariants must have explicit tests regardless of line coverage. Coverage thresholds per module and numeric latency/quality/recovery targets are agreed when a runnable baseline exists. Record measured values and hardware; never claim the design meets unmeasured targets.
