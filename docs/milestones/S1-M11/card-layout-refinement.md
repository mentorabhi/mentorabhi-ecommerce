# Storefront image containment and banner removal

2026-10-25 · User revision · R29/AE29 · Reviewed before implementation.

Tall product photographs, particularly pads, must fit inside each card's fixed image area without covering the brand, title, rating, description or price. Preserve the full photograph with object-fit containment. Apply the shared card layout to browse/search/category, wishlist and Similar Products. Keep desktop and mobile dimensions responsive.

Remove the large promotional storefront banner from home/category/search pages. Keep the small header logo, navigation and original branding assets. Admin login artwork is outside this storefront change.

The existing image button is a fixed-height grid whose image's intrinsic minimum sizing can exceed its track. Use an explicit block image frame with clipped overflow and a bounded block image; resolve percentage height against the known content box and retain object-fit: contain. Do not mask the problem by clipping an oversized image alone.

Reviewed invariants: image/button remains clickable and accessible; tall images fit completely; the text body remains in normal flow; shared card consumers receive the same containment; header branding remains; product content/pricing/reviews are unchanged. See the [editable layout](card-layout.mmd).

Verification: observe a failing browser geometry check on real pads before the CSS fix, then test desktop and 390px mobile image/frame/body bounds and photograph decoding. Check banner absence and header logo on home/category/search, build the frontend and run the affected product-experience regression. Pure CSS/markup uses actual browser geometry rather than a source-mirroring unit assertion; existing frontend rule units remain applicable.

## Executed verification

The original Selenium geometry check failed at both 1440px and 390px widths (5.365s); the mobile photo extended approximately 61px beyond its image frame. The banner check failed on all three routes (4.605s). Receipts are ignored local files under `devops/.local/verification/` (`s1-m11-pad-layout-red.log`, `s1-m11-banner-red.log`).

After the shared block-frame fix and removal of the storefront banner markup:

- Docker frontend production build (TypeScript + Vite) and deployment health gate passed: `s1-m11-layout-build.log`.
- `.venv/bin/python -m unittest discover -s apps/storefront/tests -p test_demo_catalog_ui.py -v`: **3/3 passed, 13.749s**, including both widths, genuine portrait photos, banner absence on home/category/search, header logo and existing image/price/variant/batched-request behavior (`s1-m11-layout-green.log`).
- `.venv/bin/python -m unittest discover -s apps/storefront/tests -p test_product_experience_ui.py -v`: **3 executed passes, 1 explicit delivered-review-fixture skip, 26.140s**. Desktop/mobile detail/gallery, ratings/similar navigation and variant/cart restoration passed (`s1-m11-layout-product-regression.log`). This rerun does not claim new review-moderation evidence; the earlier delivered-fixture run remains recorded in M11 verification.
- Pinned Node 24.22.1 `node --experimental-strip-types --test tests/order-freshness.test.ts tests/catalog-experience.test.ts`: **8/8 passed** using the locked Node image and a read-only frontend mount.

Host diff review checked the shared frame, full-photo containment, unchanged accessible image button and header branding. This is not an independent formal review receipt. No database schema/data, service API or credentials changed. Original banner assets remain available for historical branding/Admin artwork. Owner checks below remain separate and unchecked.

Desktop and mobile screenshot inspection also confirmed that pad photographs are fully contained above the text. The first screenshot harness waited for offscreen lazy images and timed out; it was corrected to wait for visible images. This diagnostic attempt is not counted as a test pass.
