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

    def _login_orders(self):
        self.driver.get(BASE_URL + "/orders")
        self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Sign in')]"))).click()
        self.wait.until(EC.visibility_of_element_located((By.ID,"username"))).send_keys("checkout-test-customer")
        self.driver.find_element(By.ID,"password").send_keys(self.password)
        self.driver.find_element(By.ID,"kc-login").click()
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR,'nav[aria-label="Shopping"] a[href="/orders"]')))
        self.driver.find_element(By.CSS_SELECTOR,'nav[aria-label="Shopping"] a[href="/orders"]').click()

    def test_customer_can_read_and_open_projected_order(self):
        self.driver.get(BASE_URL + "/orders")
        self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Sign in')]"))).click()
        self.wait.until(EC.visibility_of_element_located((By.ID, "username"))).send_keys("checkout-test-customer")
        self.driver.find_element(By.ID, "password").send_keys(self.password)
        self.driver.find_element(By.ID, "kc-login").click()
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'nav[aria-label="Shopping"] a[href="/orders"]')))
        self.driver.find_element(By.CSS_SELECTOR, 'nav[aria-label="Shopping"] a[href="/orders"]').click()
        self.wait.until(EC.visibility_of_element_located((By.XPATH, "//section[contains(@class,'customer-page')]//h1[normalize-space()='Your orders']")))
        status = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '[data-freshness-state="CURRENT"]')))
        self.assertIn("connected", status.text)
        self.driver.set_window_size(390, 844)
        self.assertTrue(status.is_displayed())
        self.assertLessEqual(status.rect["x"] + status.rect["width"], self.driver.execute_script("return window.innerWidth"))
        self.driver.set_window_size(1440, 1000)
        row = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".order-row")))
        self.assertTrue(row.find_elements(By.CSS_SELECTOR, ".order-state"))
        row.click()
        detail = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".order-detail")))
        self.assertTrue(detail.find_elements(By.CSS_SELECTOR, ".order-line"))
        self.assertTrue(detail.find_elements(By.TAG_NAME, "address"))

    def test_customer_sees_blocked_gap_and_authoritative_order_fallback(self):
        expected_order=os.environ.get("SUPERSPORTS_FRESHNESS_PROBE_ORDER_ID")
        if not expected_order:self.skipTest("This Selenium journey runs only while the isolated M06 gap probe is active.")
        self._login_orders()
        try:
            status=self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR,'[data-freshness-state="BLOCKED"]')))
        except Exception as error:
            raise AssertionError(f"blocked freshness banner missing at {self.driver.current_url}: {self.driver.find_element(By.TAG_NAME,'body').text[:1200]}") from error
        self.assertIn("need attention",status.text.lower())
        expected_prefix=expected_order[:8].upper()
        rows=self.wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR,".order-row")))
        self.assertTrue(any(expected_prefix in row.text for row in rows),"blocked projection must fall back to current owned Orders records")

    def test_customer_sees_unavailable_stream_and_owned_order_fallback(self):
        expected_order=os.environ.get("SUPERSPORTS_FRESHNESS_PROBE_ORDER_ID")
        if not expected_order:self.skipTest("This Selenium journey runs only while the isolated M06 outage probe is active.")
        self._login_orders()
        status=self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR,'[data-freshness-state="UNAVAILABLE"]')))
        self.assertIn("temporarily unavailable",status.text.lower())
        expected_prefix=expected_order[:8].upper()
        rows=self.wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR,".order-row")))
        self.assertTrue(any(expected_prefix in row.text for row in rows),"unavailable history must fall back to current owned Orders records")

    def test_customer_can_cancel_a_synthetic_order_before_handoff(self):
        expected_order=os.environ.get("SUPERSPORTS_CANCELLABLE_ORDER_ID")
        if not expected_order:self.skipTest("Provide a synthetic scheduled order ID dedicated to cancellation acceptance.")
        self._login_orders()
        prefix=expected_order[:8].upper()
        rows=self.wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR,".order-row")))
        matching=next((row for row in rows if prefix in row.text),None)
        self.assertIsNotNone(matching,"the authenticated customer must see the prepared owned order")
        matching.click()
        button=self.wait.until(EC.element_to_be_clickable((By.XPATH,"//button[normalize-space()='Cancel order']")))
        button.click()
        self.wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR,".order-detail h2"),"CANCELLED"))
        status=self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR,".order-detail [role='status']")))
        self.assertIn("completed",status.text.lower())

    def test_customer_can_request_one_partial_return_for_a_delivered_order(self):
        expected_order=os.environ.get("SUPERSPORTS_RETURNABLE_ORDER_ID")
        if not expected_order:self.skipTest("Provide a dedicated delivered order with at least one returnable unit.")
        self._login_orders()
        prefix=expected_order[:8].upper()
        rows=self.wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR,".order-row")))
        matching=next((row for row in rows if prefix in row.text),None)
        self.assertIsNotNone(matching,"the authenticated customer must see the delivered order")
        matching.click()
        self.wait.until(EC.element_to_be_clickable((By.XPATH,"//button[normalize-space()='Return 1 unit']"))).click()
        self.wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR,".return-status"),"completed"))
        status=self.driver.find_element(By.CSS_SELECTOR,".return-status")
        self.assertIn("simulated refund",status.text.lower())

    def test_customer_can_create_and_reply_to_owned_support_ticket(self):
        self._login_orders()
        self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR,'a[href="/account#support"]'))).click()
        subject="Selenium support request"
        self.wait.until(EC.visibility_of_element_located((By.NAME,"subject"))).send_keys(subject)
        self.driver.find_element(By.NAME,"message").send_keys("Please explain the local delivery estimate.")
        self.driver.find_element(By.XPATH,"//button[normalize-space()='Create support request']").click()
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR,".order-detail")))
        self.assertIn(subject,self.driver.find_element(By.CSS_SELECTOR,".order-detail").text)
        self.driver.find_element(By.CSS_SELECTOR,".order-detail textarea[name='message']").send_keys("Adding a follow-up question.")
        self.driver.find_element(By.XPATH,"//button[normalize-space()='Send reply']").click()
        self.wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR,".order-detail"),"Adding a follow-up question."))

    def test_customer_can_submit_review_for_delivered_purchase(self):
        expected_order=os.environ.get("SUPERSPORTS_REVIEWABLE_ORDER_ID")
        if not expected_order:self.skipTest("Provide a synthetic delivered owned order for review acceptance.")
        self._login_orders();prefix=expected_order[:8].upper()
        rows=self.wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR,".order-row")))
        matching=next((row for row in rows if prefix in row.text),None)
        self.assertIsNotNone(matching);matching.click()
        form=self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR,"form.address-form")))
        form.find_element(By.NAME,"title").send_keys("Selenium verified review")
        form.find_element(By.NAME,"body").send_keys("Synthetic review submitted for moderation.")
        form.find_element(By.XPATH,".//button[normalize-space()='Submit review']").click()
        self.wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR,".store-alert.success"),"moderation"))


if __name__ == "__main__":
    unittest.main()
