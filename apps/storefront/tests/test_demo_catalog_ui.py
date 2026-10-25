"""Selenium checks for the M10 catalog images, pricing, variants and batched snapshots."""
import unittest

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
        self.wait.until(EC.presence_of_element_located((By.XPATH, "//button[contains(., 'Tournament Willow Cricket Bat')]")))
        self.wait.until(lambda driver: driver.execute_script(
            "return [...document.querySelectorAll('.store-card-image img')].length > 0 && "
            "[...document.querySelectorAll('.store-card-image img')].every(image => image.complete && image.naturalWidth > 0)"))
        self.assertNotIn("Price unavailable", self.driver.find_element(By.CSS_SELECTOR, ".store-product-grid").text)
        counts = self.driver.execute_script("""
          const entries = performance.getEntriesByType('resource').map(item => item.name);
          return {
            prices: entries.filter(url => url.includes('/api/pricing/public/skus?skuIds=')).length,
            stock: entries.filter(url => url.includes('/api/inventory/availability?skuIds=')).length
          };
        """)
        self.assertEqual(counts, {"prices": 2, "stock": 2})
        card = self.driver.find_element(By.XPATH, "//article[contains(@class,'store-card')][.//button[contains(., 'Tournament Willow Cricket Bat')]]")
        image_link = card.find_element(By.CSS_SELECTOR, ".store-card-image")
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'})", image_link)
        self.wait.until(EC.element_to_be_clickable(image_link)).click()
        selector = self.wait.until(EC.visibility_of_element_located((By.XPATH, "//label[contains(., 'Choose your option')]/select")))
        self.assertEqual(len(selector.find_elements(By.TAG_NAME, "option")), 10)
        detail_image = self.driver.find_element(By.CSS_SELECTOR, ".detail-image img")
        self.assertGreater(self.driver.execute_script("return arguments[0].naturalWidth", detail_image), 0)


if __name__ == "__main__":
    unittest.main()
