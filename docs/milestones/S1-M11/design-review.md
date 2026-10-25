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
