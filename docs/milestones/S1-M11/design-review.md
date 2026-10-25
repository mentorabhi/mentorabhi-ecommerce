# Initial design review

2026-10-25 · Review before implementation

- Resolved hierarchy: model/brand product → size/colour SKU; both sport-level minimums are independent.
- Historical integrity: retirement replaces active listings without deleting order facts or resetting databases.
- Ratings integrity: demo seed has explicit provenance; true customer reviews retain delivered-purchase checks and moderation. Public summaries count only published rows and cannot leak owner/order IDs.
- Scale: paginated catalog/direct detail, bounded snapshot/summary batches and local thumbnails avoid the current first-100-products cap and excessive requests.
- Frontend separation: separate projects, builds, origins, callbacks and themes; legacy Admin bookmarks redirect.
- Access scope: admin/admin applies to human operational UIs, while the customer realm and service/database credentials retain their separate trust boundaries.
- Open implementation constraint: direct retailer/catalog HTTP intake returned rate-limit responses during initial research. No source/photos are accepted yet; select accessible, attributed sources and validate actual photo/model correspondence before activation. Amazon's live page could not be retrieved; Flipkart listing and the attached similar-products reference informed structure only.

The architecture is ready for U1/U2 implementation. U3 cannot be marked complete until real assets, model/variant counts and provenance are measured. No requirement is silently waived by source unavailability.

U2 moderation refinement: the existing pending-only Admin queue cannot satisfy the documented hide-published-review journey. Add an operator-only bounded state filter and a Hide action for published rows, retaining existing audited transitions and no hidden-row republish. Public summaries remain derived from PUBLISHED rows. Review confirmed the API remains operator-scoped and introduces no new data owner or permission model.

U4 browser review: Admin must serve the same readable local photographic assets as storefront and its product form must accept the backend-supported JPG/JPEG/PNG/WebP keys alongside legacy SVG. Browser fixtures select active sourced products for stock mutations; retired historical SKUs remain read-only evidence. Catalog creation uses a unique test slug and a real existing local photo, followed by owner-API retirement during final cleanup. No new service or architecture boundary is introduced.

Final browser refinement: SupportPanel renders the created ticket before its follow-up list refresh completes, and the shared busy state intentionally disables Send reply until that action finishes. The existing Selenium journey clicked without waiting for enabled state; the failed run retained only the initial message, while prior runs had both. Use a unique subject and wait for the reply button to become clickable, retaining the required persisted reply assertion. No production behavior or timeout changes are needed.
