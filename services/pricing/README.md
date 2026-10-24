# Pricing service

Pricing owns the active store currency, INR/USD price books, coupon definitions and price revisions. Money is an integer count of paise or cents; no exchange rates are applied. Catalog activation calls the scoped completeness endpoint. Coupon definitions do not reserve or consume usage limits; checkout owns those rules in S1-M05.

Public API contract: `../../contracts/pricing/openapi.yaml`.
