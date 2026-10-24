# S1-M05 design review

Revision 2 · 2026-10-24 · Independent review findings resolved; ready for implementation design gate.

## Coverage

- **Security and transaction correctness review:** completed by session reviewer Gibbs.
- **Architecture, reliability and resource review:** completed by session reviewer Lagrange.
- **Follow-up:** both reviewers re-checked the corrected design and diagram twice; the final review confirms no remaining blockers.
- **Author synthesis:** findings checked against accepted requirements, current service APIs, ADRs 0002–0004, and the proposed `checkout-saga.mmd`.
- **External model review:** not run; review used session reviewers only, consistent with the local-only review policy.

## Findings and resolutions

| Finding | Consequence | Resolution in design |
|---|---|---|
| Inventory reservation had no authoritative finalization step. | A confirmed order could leave stock reserved or allow an expired sold unit to become available again. | Defined Inventory `HELD → PROTECTED → COMMITTED` and release/expiry states, atomic consume movement, owning-service commit API, and post-capture recovery. |
| Coupon hold was described as though Orders could commit Pricing-owned data. | Coupon limits could be exceeded or a confirmed order could retain an expiring hold. | Added Pricing-owned protect/commit/release operations and count held/protected capacity against limits; finalization is a persisted Saga step. |
| Worker leases did not fence delayed/stale callers. | Two workers could advance or compensate the same workflow after lease takeover. | Added monotonic fences checked on every Orders transition and internal operation, stable operation keys/payload hashes, and stale-token rejection. |
| Checkout internal audience was not connected to the existing broad M03 API policy. | Internal service tokens could be rejected or accidentally receive operator access. | Dedicated `supersports-checkout-worker` client, internal-only audience, exact issuer/`aud`/`azp`/scope checks and `/api/v1/internal/checkout/**` route separation; negative tests are required. |
| Async workflow could need the customer address after the customer token had expired. | Worker might persist/forward a bearer token or fail restart recovery. | Retrieve and validate the address synchronously in the authenticated request, store the immutable address snapshot, discard the token, and queue only durable workflow state. |
| Pricing reads and coupon computation were not bound to one consistent quote. | Currency/prices/rules could change between reads and produce a mismatched order total. | Added one authoritative Pricing quote/revision operation and require coupon hold to bind that quote; stale revisions conflict before reservations. |
| Pricing lacked trustworthy Catalog facts for category-based coupon eligibility. | Pricing could not apply product/category restrictions without private-table access or browser-controlled category claims. | Added an authenticated internal Catalog lookup; Orders supplies Catalog-sourced facts to Pricing through its scoped service identity, avoiding a Pricing→Catalog dependency cycle. |
| Global idempotency keys allowed cross-customer key squatting/data leakage. | A different customer could deny checkout or infer whether a key was used. | Scope idempotency uniqueness to `(customer_subject, idempotency_key)` and make other subjects independent. |
| Idempotency was recorded after mutable quote/address reads. | A same-key retry could observe changed coupon, price or address instead of replaying the original order; concurrent first requests could both validate. | Claim the scoped key and payload hash first, model `VALIDATING`/`ACCEPTED`/`REJECTED`, use a short validation lease, resolve unique-key races by reading the owner's state, and only enqueue side effects after order plus Saga are committed. |
| Payment ambiguity lacked a concrete operation reconciliation contract. | A lost capture response could cause unsafe release or duplicate capture. | Added durable simulator operation ledger, status lookup by stable order/step identity and payload-hash conflict rules; reconcile before retry/void/refund/release. |
| Resource capacity needed explicit measured acceptance. | New Java services could exceed local Docker allocation during startup or concurrent tests. | Recorded current measured baseline separately; require full-profile startup, concurrent test and peak `docker stats` measurements against the 7.75 GiB Docker allocation. |

## Remaining observations

- The existing Excalidraw M05 diagram remains a historical proposal. The new editable Mermaid diagram includes Configuration and the checkout identity path and is the reviewed implementation contract; the release diagram must be updated if implementation changes service boundaries or step order.
- The design is for the local learning profile. It does not establish a production legal retention period for address snapshots, a production SLO, high availability, or scale target.
- The current M04 stack's measured sample is 2,112.6 MiB RSS across eight containers with 7.75 GiB allocated to Docker. Adding three Java simulator/order containers at 512 MiB limits each would bring the configured caps to approximately 5.25 GiB; this supports feasibility for a local profile but is not a startup, peak, or concurrency measurement. M05 must measure those results before claiming 16 GB acceptance.
- No blocking design finding remains. Implementation can start from the reviewed contracts and test gates.
