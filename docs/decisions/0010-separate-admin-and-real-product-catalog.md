# ADR 0010 — Separate Admin and sourced product/review data

Date: 2026-10-25 · Status: accepted for S1-M11 design; implementation pending

The user revised the storefront scale and presentation after the original Stage 1 automated acceptance. Model each real branded product separately from its sellable size/colour SKU variants. Require at least 100 active products/1,000 active SKUs per sport, genuine local product photographs with source provenance, fuller details, public published-rating summaries/reviews and a bounded similar-product row. Preserve immutable historical orders when retiring old fictional active fixtures.

Separate customer UI in apps/storefront (localhost:3000) from Admin in apps/admin (localhost:3002), each with its own build/container/theme and identity callbacks. Legacy /admin links redirect to the new origin. Shared branding/assets do not require shipping operational application code in the storefront bundle.

Seed 3–4 deterministic demo reviews per product with explicit provenance and 3–5 ratings. Demo reviews never claim a verified delivered purchase. Actual customer reviews retain owner-side delivered-purchase verification and moderation; aggregates count only published rows and omit private identities.

The user's admin/admin revision applies to human operational UI access. Provision and document that login for each enabled UI while keeping the storefront customer realm and service/CDC/database credentials separate. All interfaces remain loopback-bound, and optional profiles remain explicit on the 16 GB host.

Implementation, tests and source/asset acceptance follow the S1-M11 reviewed design. Source feed unavailability cannot justify fictional photos/model claims or marking the requested counts complete. OpenTelemetry is a separate R28/S1-M12 follow-up to ADR 0009.
