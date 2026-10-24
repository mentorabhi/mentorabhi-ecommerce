# S1-M08 standard commerce metrics — design review

Revision 1 · 2026-10-24 · Reviewed before implementation

- **Ownership:** all measures use published Order lifecycle facts already ingested by M08. No cross-service table reads or new event contracts are required.
- **Money meaning:** distinguish merchandise subtotal, discounts, order total, refunds, and period net cash sales. Do not label total inclusive of tax/shipping as GMV.
- **Refund timing:** subtract refunds in their own event period; document this as period activity rather than lifetime order-cohort net sales.
- **Rates:** discount rate divides confirmed discounts by confirmed GMV; refund amount rate divides refund amount issued during the period by order value accepted during the period. Both remain period activity ratios and are labeled accordingly.
- **Currency:** every query filters a single supported currency. No conversion or cross-currency aggregation.
- **Double counting:** confirmed sales require an accepted order and a confirmation fact. Refunds use immutable event IDs in the deduplicated raw table. Cancellation and return-request counts stay separate from refund amounts.
- **Range:** limit periods to the documented 7–365 days. Keep SQL values bounded and interpolated only after strict validation.
- **Privacy:** no customer digest, coupon code, or sensitive attributes are needed for these measures. Funnel, customer, promotion attribution and inventory health stay out until a reviewed source is available.
- **Capacity:** add bounded aggregate queries to the existing optional Trino API; do not add a resident service or change the core profile.
- **Testing sequence:** add unit and Selenium test sources now; execute only after all Stage 1 development, beginning at the open M06 gates.

Review outcome: approved for implementation within the stated scope. No blocking design issue found.
