"""Selenium checks for the M10 catalog images, pricing, variants and batched snapshots."""
import unittest
import json
import math
from urllib.request import urlopen

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class DemoCatalogUiTests(unittest.TestCase):
    def setUp(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1440,1000")
        options.add_argument("--disable-dev-shm-usage")
        self.driver = webdriver.Chrome(options=options)
        self.addCleanup(self.driver.quit)
        self.wait = WebDriverWait(self.driver, 30)

    def test_demo_products_render_local_images_prices_and_variants_with_bounded_requests(self):
        self.driver.get("http://localhost:3000/")
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".store-product-grid")))
        with urlopen("http://localhost:3000/api/catalog/public/products?pageSize=24", timeout=10) as response:
            products = json.load(response)["items"]
        product = next(item for item in products if len(item["skus"]) > 1)
        self.wait.until(lambda driver: len(driver.find_elements(By.CSS_SELECTOR, ".store-product-grid .store-card")) == len(products))
        for card in self.driver.find_elements(By.CSS_SELECTOR, ".store-product-grid .store-card"):
            image = card.find_element(By.CSS_SELECTOR, ".store-card-image img")
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'})", image)
            self.wait.until(lambda driver: driver.execute_script("return arguments[0].complete && arguments[0].naturalWidth > 0", image))
        self.wait.until(lambda driver: "Price unavailable" not in driver.find_element(By.CSS_SELECTOR, ".store-product-grid").text)
        self.assertNotIn("Price unavailable", self.driver.find_element(By.CSS_SELECTOR, ".store-product-grid").text)
        counts = self.driver.execute_script("""
          const entries = performance.getEntriesByType('resource').map(item => item.name);
          return {
            prices: entries.filter(url => url.includes('/api/pricing/public/skus?skuIds=')).length,
            stock: entries.filter(url => url.includes('/api/inventory/availability?skuIds=')).length
          };
        """)
        expected = math.ceil(len({sku["id"] for item in products for sku in item["skus"]}) / 100)
        self.assertEqual(counts, {"prices": expected, "stock": expected})
        card = self.driver.find_element(By.CSS_SELECTOR, f'.store-card[data-product-id="{product["id"]}"]')
        image_link = card.find_element(By.CSS_SELECTOR, ".store-card-image")
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'})", image_link)
        self.wait.until(EC.element_to_be_clickable(image_link)).click()
        selector = self.wait.until(EC.visibility_of_element_located((By.XPATH, "//label[contains(., 'Choose your option')]/select")))
        self.assertEqual(len(selector.find_elements(By.TAG_NAME, "option")), len(product["skus"]))
        detail_image = self.driver.find_element(By.CSS_SELECTOR, ".detail-image img")
        self.assertGreater(self.driver.execute_script("return arguments[0].naturalWidth", detail_image), 0)


if __name__ == "__main__":
    unittest.main()
