"""Selenium smoke for customer sign-in and the asynchronous order history screen."""
from __future__ import annotations

import os
from pathlib import Path
import unittest

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


ROOT = Path(__file__).resolve().parents[3]
BASE_URL = os.environ.get("SUPERSPORTS_UI_URL", "http://localhost:3000")


class CustomerOrderHistoryUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        credentials = {}
        for line in (ROOT / "devops/.local/bootstrap.env").read_text().splitlines():
            key, separator, value = line.partition("=")
            if separator and key == "DEMO_CUSTOMER_PASSWORD":
                credentials[key] = value
        if "DEMO_CUSTOMER_PASSWORD" not in credentials:
            raise RuntimeError("Run devops/scripts/supersports configure before Selenium UI checks.")
        cls.password = credentials["DEMO_CUSTOMER_PASSWORD"]

    def setUp(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1440,1000")
        options.add_argument("--disable-dev-shm-usage")
        self.driver = webdriver.Chrome(options=options)
        self.addCleanup(self.driver.quit)
        self.wait = WebDriverWait(self.driver, 25)

    def test_customer_can_read_and_open_projected_order(self):
        self.driver.get(BASE_URL + "/orders")
        self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Sign in')]"))).click()
        self.wait.until(EC.visibility_of_element_located((By.ID, "username"))).send_keys("checkout-test-customer")
        self.driver.find_element(By.ID, "password").send_keys(self.password)
        self.driver.find_element(By.ID, "kc-login").click()
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'nav[aria-label="Shopping"] a[href="/orders"]')))
        self.driver.find_element(By.CSS_SELECTOR, 'nav[aria-label="Shopping"] a[href="/orders"]').click()
        self.wait.until(EC.visibility_of_element_located((By.XPATH, "//section[contains(@class,'customer-page')]//h1[normalize-space()='Your orders']")))
        row = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".order-row")))
        self.assertTrue(row.find_elements(By.CSS_SELECTOR, ".order-state"))
        row.click()
        detail = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".order-detail")))
        self.assertTrue(detail.find_elements(By.CSS_SELECTOR, ".order-line"))
        self.assertTrue(detail.find_elements(By.TAG_NAME, "address"))


if __name__ == "__main__":
    unittest.main()
