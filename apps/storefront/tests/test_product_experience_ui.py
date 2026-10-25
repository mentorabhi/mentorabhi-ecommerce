"""Selenium coverage for M11 public shopping, exact variants and review moderation."""
import json
from decimal import Decimal, ROUND_HALF_UP
import os
from pathlib import Path
import sys
import unittest
import uuid
from urllib.request import urlopen

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "devops/scripts"))
import manage


def public(path):
    with urlopen("http://localhost:3000/api/" + path, timeout=15) as response:
        return json.load(response)


def rating_label(summary):
    if not summary["count"] or summary["mean"] is None:
        return "No reviews yet"
    # Match decimal display of the actual binary number, with ties rounded
    # away from zero as Number.toFixed specifies (Python format uses ties-even).
    mean = Decimal.from_float(float(summary["mean"])).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return f'{mean} out of 5 · {summary["count"]} reviews'


class ProductExperienceUiTests(unittest.TestCase):
    def setUp(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1440,1100")
        options.add_argument("--disable-dev-shm-usage")
        self.driver = webdriver.Chrome(options=options)
        self.addCleanup(self.driver.quit)
        self.wait = WebDriverWait(self.driver, 30)

    def open_product(self, product):
        self.driver.get("http://localhost:3000/products/" + product["slug"])
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, f'.detail-layout[data-product-id="{product["id"]}"]')))
        self.wait.until(lambda driver: driver.execute_script("return document.querySelector('.detail-image img')?.naturalWidth > 0"))

    def customer_login(self):
        credentials = manage.load_credentials(ROOT / "devops/.local/bootstrap.env")
        self.driver.get("http://localhost:3000/account")
        self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Sign in or create account']"))).click()
        self.wait.until(EC.presence_of_element_located((By.NAME, "username"))).send_keys("checkout-test-customer")
        self.driver.find_element(By.NAME, "password").send_keys(credentials["DEMO_CUSTOMER_PASSWORD"] + Keys.ENTER)
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".shop-shell")))
        self.wait.until(lambda driver: "Account" in driver.find_element(By.CSS_SELECTOR, ".shop-actions").text)
        return manage.customer_token_for("checkout-test-customer", credentials["DEMO_CUSTOMER_PASSWORD"])

    def assert_gallery_fits(self):
        bounds = self.driver.execute_script("""
          const image = document.querySelector('.detail-image img').getBoundingClientRect();
          const frame = document.querySelector('.detail-image').getBoundingClientRect();
          return {left:image.left, right:image.right, top:image.top, bottom:image.bottom,
                  frameLeft:frame.left, frameRight:frame.right, frameTop:frame.top, frameBottom:frame.bottom};
        """)
        self.assertGreaterEqual(bounds["left"], bounds["frameLeft"])
        self.assertLessEqual(bounds["right"], bounds["frameRight"])
        self.assertGreaterEqual(bounds["top"], bounds["frameTop"])
        self.assertLessEqual(bounds["bottom"], bounds["frameBottom"])

    def test_ratings_agree_on_browse_search_detail_and_similar_navigation(self):
        product = public("catalog/public/products?pageSize=1")["items"][0]
        summary = public("reviews/reviews/products/summaries?productIds=" + product["id"])[0]
        self.assertGreaterEqual(summary["count"], 3, "Run the M11 demo seed/integration fixture first")
        expected = rating_label(summary)
        self.driver.get("http://localhost:3000/")
        selector = f'.store-card[data-product-id="{product["id"]}"] .product-rating'
        self.wait.until(lambda driver: driver.find_element(By.CSS_SELECTOR, selector).get_attribute("aria-label") == expected)
        search = self.driver.find_element(By.ID, "store-search")
        search.send_keys(product["title"] + Keys.ENTER)
        self.wait.until(lambda driver: product["title"] in driver.find_element(By.CSS_SELECTOR, ".collection-heading h1").text)
        self.wait.until(lambda driver: driver.find_element(By.CSS_SELECTOR, selector).get_attribute("aria-label") == expected)
        self.driver.find_element(By.CSS_SELECTOR, f'.store-card[data-product-id="{product["id"]}"] .store-card-image').click()
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".product-reviews")))
        self.wait.until(lambda driver: driver.find_element(By.CSS_SELECTOR, ".detail-copy .product-rating").get_attribute("aria-label") == expected)
        self.wait.until(lambda driver: len(driver.find_elements(By.CSS_SELECTOR, ".review-badge.demo")) >= 3)
        self.assert_gallery_fits()
        similar = self.driver.find_elements(By.CSS_SELECTOR, ".similar-item .store-card")
        self.assertGreater(len(similar), 0)
        self.assertLessEqual(len(similar), 12)
        self.assertNotIn(product["id"], [card.get_attribute("data-product-id") for card in similar])
        target = similar[0].get_attribute("data-product-id")
        button = similar[0].find_element(By.CSS_SELECTOR, ".store-card-image")
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'})", button)
        button.click()
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, f'.detail-layout[data-product-id="{target}"]')))

    def test_mobile_gallery_arrows_and_direct_product_route(self):
        product = public("catalog/public/products?pageSize=1")["items"][0]
        self.driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {"width": 390, "height": 844, "deviceScaleFactor": 1, "mobile": True})
        self.open_product(product)
        self.assert_gallery_fits()
        self.assertEqual(self.driver.execute_script("return innerWidth"), 390)
        self.assertFalse(self.driver.execute_script("return document.documentElement.scrollWidth > innerWidth"))
        rail = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".similar-rail")))
        button = self.driver.find_element(By.CSS_SELECTOR, "button[aria-label='Next similar products']")
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'})", button)
        button.click()
        self.wait.until(lambda driver: driver.execute_script("return document.querySelector('.similar-rail').scrollLeft > 0"))
        rail.send_keys(Keys.ARROW_LEFT)

    def test_selected_variant_survives_fresh_cart_navigation_and_restores_original_quantity(self):
        token = self.customer_login()
        page = public("catalog/public/products?pageSize=24")
        last = max(1, (page["total"] + 23) // 24)
        products = public(f"catalog/public/products?pageSize=24&page={last}")["items"]
        product = next(item for item in products if len(item["skus"]) > 1)
        available = public("inventory/availability?skuIds=" + ",".join(item["id"] for item in product["skus"][:100]))
        stocked = {item["skuId"] for item in available if item["available"] > 0}
        sku = next(item for item in reversed(product["skus"]) if item["id"] in stocked)
        url = "http://127.0.0.1:8085/api/v1/customer/cart"
        status, original = manage.request_json(url, token=token)
        self.assertEqual(status, 200)
        quantity = next((item["quantity"] for item in original if item["skuId"] == sku["id"]), 0)
        self.assertLess(quantity, 99)
        try:
            self.open_product(product)
            self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Add to cart']")))
            Select(self.driver.find_element(By.XPATH, "//label[contains(.,'Choose your option')]/select")).select_by_value(sku["id"])
            self.assertEqual(self.driver.find_element(By.CSS_SELECTOR, ".detail-layout").get_attribute("data-selected-sku"), sku["id"])
            self.driver.find_element(By.XPATH, "//button[normalize-space()='Add to cart']").click()
            self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".store-alert.success")))
            self.driver.get("http://localhost:3000/cart")
            self.wait.until(lambda driver: sku["code"] in driver.find_element(By.CSS_SELECTOR, ".customer-page").text)
            status, current = manage.request_json(url, token=token)
            self.assertEqual(status, 200)
            self.assertEqual(next(item["quantity"] for item in current if item["skuId"] == sku["id"]), quantity + 1)
        finally:
            item_url = url + "/items/" + sku["id"]
            status, _ = manage.request_json(item_url, token=token, method="PUT" if quantity else "DELETE", data=json.dumps({"quantity": quantity}).encode() if quantity else None)
            self.assertIn(status, (200, 204))

    @unittest.skipUnless(os.getenv("SUPERSPORTS_REVIEW_FIXTURE"), "Prepare a new delivered M11 review fixture")
    def test_product_review_submission_publish_hide_and_public_counts(self):
        fixture = json.loads(Path(os.environ["SUPERSPORTS_REVIEW_FIXTURE"]).read_text())
        token = self.customer_login()
        self.open_product({"id": fixture["productId"], "slug": fixture["productSlug"]})
        before = public("reviews/reviews/products/summaries?productIds=" + fixture["productId"])[0]["count"]
        write = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Write a review']")))
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'})", write)
        write.click()
        order = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[aria-label='Review purchase order']")))
        Select(order).select_by_value(fixture["orderId"])
        title = "M11 browser review " + uuid.uuid4().hex[:8]
        form = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".review-form")))
        Select(form.find_element(By.NAME, "skuId")).select_by_value(fixture["skuId"])
        Select(form.find_element(By.NAME, "rating")).select_by_value("4")
        form.find_element(By.NAME, "title").send_keys(title)
        form.find_element(By.NAME, "body").send_keys("Synthetic browser acceptance feedback for a delivered purchase.")
        form.find_element(By.CSS_SELECTOR, "button").click()
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".review-success")))
        self.assertEqual(public("reviews/reviews/products/summaries?productIds=" + fixture["productId"])[0]["count"], before)
        status, owned = manage.request_json("http://127.0.0.1:8092/api/v1/customer/reviews", token=token)
        self.assertEqual(status, 200)
        review = next(row for row in owned if row["title"] == title)
        self.assertEqual(review["state"], "PENDING")

        self.driver.get("http://localhost:3002/admin")
        self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(.,'Sign in with local account')]"))).click()
        self.wait.until(EC.presence_of_element_located((By.NAME, "username"))).send_keys("admin")
        self.driver.find_element(By.NAME, "password").send_keys("admin" + Keys.ENTER)
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".app-shell")))
        self.driver.find_element(By.XPATH, "//nav[@aria-label='Workspace sections']//button[contains(.,'Reviews')]").click()
        selector = f'article[data-review-id="{review["reviewId"]}"]'
        row = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, selector)))
        row.find_element(By.XPATH, ".//button[normalize-space()='Publish']").click()
        self.wait.until(lambda driver: public("reviews/reviews/products/summaries?productIds=" + fixture["productId"])[0]["count"] == before + 1)
        admin_tab = self.driver.current_window_handle
        self.driver.switch_to.new_window("tab")
        self.open_product({"id": fixture["productId"], "slug": fixture["productSlug"]})
        published = self.wait.until(EC.visibility_of_element_located((By.XPATH, f"//article[contains(@class,'review-card')][.//h3[normalize-space()='{title}']]")))
        self.assertEqual(published.find_element(By.CSS_SELECTOR, ".review-badge").text, "Verified delivered purchase")
        self.driver.close()
        self.driver.switch_to.window(admin_tab)
        Select(self.driver.find_element(By.CSS_SELECTOR, "select[aria-label='Review moderation state']")).select_by_value("PUBLISHED")
        product_filter = self.driver.find_element(By.CSS_SELECTOR, "input[aria-label='Review product ID']")
        product_filter.send_keys(fixture["productId"] + Keys.ENTER)
        row = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, selector)))
        row.find_element(By.XPATH, ".//button[normalize-space()='Hide review']").click()
        self.wait.until(lambda driver: public("reviews/reviews/products/summaries?productIds=" + fixture["productId"])[0]["count"] == before)
        self.open_product({"id": fixture["productId"], "slug": fixture["productSlug"]})
        after = public("reviews/reviews/products/summaries?productIds=" + fixture["productId"])[0]
        label = rating_label(after)
        self.wait.until(lambda driver: driver.find_element(By.CSS_SELECTOR, ".product-reviews .product-rating").get_attribute("aria-label") == label)
        self.assertFalse(self.driver.find_elements(By.XPATH, f"//h3[normalize-space()='{title}']"))
