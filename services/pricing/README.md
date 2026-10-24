# Pricing service

Pricing owns the active store currency, INR/USD price books, coupon definitions and price revisions. Money is an integer count of paise or cents; no exchange rates are applied. Catalog activation calls the scoped completeness endpoint. The M05 internal checkout API stores five-minute owner-bound quote snapshots and atomically reserves global/per-customer coupon capacity with protected, committed and released states. Coupon percentages round half-up; eligible line allocations use largest remainder and SKU UUID tie-breaking. Internal routes require the exact checkout worker client, audience and per-operation scope. The Orders Saga is not yet wired to these operations.

Public API contract: `../../contracts/pricing/openapi.yaml`.
