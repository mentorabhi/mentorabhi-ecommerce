"""Selenium end-to-end checks for the local SuperSports admin workspace."""
from __future__ import annotations

from datetime import datetime, timedelta
import os
from pathlib import Path
import time
import unittest
import uuid
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait


ROOT = Path(__file__).resolve().parents[3]
BASE_URL = os.environ.get("SUPERSPORTS_UI_URL", "http://localhost:3000")
BOOTSTRAP_FILE = ROOT / "devops/.local/bootstrap.env"
TEST_PRODUCT_TITLE = "Selenium UI Regression Item"
TEST_PRODUCT_SLUG = "selenium-ui-regression-item"
TEST_SKU_CODE = "SS-SELENIUM-UI-001"
TEST_COUPON_CODE = "SELENIUMUI"


def local_credentials() -> dict[str, str]:
    if not BOOTSTRAP_FILE.is_file():
        raise RuntimeError("Run devops/scripts/supersports configure before the Selenium UI suite.")
    allowed = {
        "DEMO_CATALOG_ADMIN_PASSWORD",
        "DEMO_PLATFORM_ADMIN_PASSWORD",
        "DEMO_CUSTOMER_PASSWORD",
    }
    values = {}
    for line in BOOTSTRAP_FILE.read_text().splitlines():
        key, separator, value = line.partition("=")
        if separator and key in allowed:
            values[key] = value
    missing = allowed - values.keys()
    if missing:
        raise RuntimeError("The local bootstrap file is missing the demo UI account credentials.")
    admin_file = ROOT / "devops/.local/admin-login.env"
    admin_value = admin_file.read_text().strip().partition("=")
    if admin_file.is_symlink() or admin_value[:2] != ("ADMIN_PASSWORD", "=") or not admin_value[2]:
        raise RuntimeError("The ignored local admin login file is missing or invalid.")
    values["ADMIN_PASSWORD"] = admin_value[2]
    return values


class SuperSportsAdminUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.credentials = local_credentials()

    def setUp(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1440,1100")
        options.add_argument("--disable-dev-shm-usage")
        self.driver = webdriver.Chrome(options=options)
        self.addCleanup(self.driver.quit)
        self.wait = WebDriverWait(self.driver, 20)

    def login(self, username: str, password_key: str):
        self.driver.get(BASE_URL)
        self.wait.until(lambda driver: driver.execute_script(
            "return document.querySelector('.brand-banner')?.naturalWidth > 0"))
        self.wait.until(lambda driver: driver.execute_script(
            "return document.querySelector('.login-brand img')?.naturalWidth > 0"))
        self.wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(., 'Sign in with local account')]"))).click()
        self.wait.until(EC.presence_of_element_located((By.NAME, "username"))).send_keys(username)
        password = self.wait.until(EC.presence_of_element_located((By.NAME, "password")))
        password.send_keys(self.credentials[password_key])
        password.send_keys(Keys.ENTER)
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".app-shell")))
        self.wait.until(EC.visibility_of_element_located(
            (By.XPATH, "//nav[@aria-label='Workspace sections']")))
        browser_auth = self.driver.execute_async_script("""
            const done = arguments[0];
            try {
              const stored = Object.values(sessionStorage).map(value => {
                try { return JSON.parse(value); } catch { return null; }
              }).find(value => value && value.access_token);
              if (!stored) return done({error:'OIDC session token missing'});
              const payload = stored.access_token.split('.')[1];
              const claims = JSON.parse(atob(payload.replace(/-/g,'+').replace(/_/g,'/') + '='.repeat((4-payload.length%4)%4)));
              Promise.all(['/api/pricing/currency','/api/inventory/balances'].map(path =>
                fetch(path, {headers:{Authorization:`Bearer ${stored.access_token}`}}).then(response => response.status)
              )).then(statuses => done({token:stored.access_token,roles:claims.realm_access?.roles??[],aud:claims.aud??[],statuses}));
            } catch (error) { done({error:String(error)}); }
        """)
        claim_summary = {"roles": browser_auth.get("roles"), "aud": browser_auth.get("aud"),
                         "proxy_statuses": browser_auth.get("statuses")}
        self.assertIn("supersports-api", browser_auth.get("aud", []), claim_summary)
        direct_statuses = []
        for url in ("http://127.0.0.1:8083/api/v1/pricing/currency",
                    "http://127.0.0.1:8084/api/v1/inventory/balances"):
            try:
                with urlopen(Request(url, headers={"Authorization": f"Bearer {browser_auth['token']}"}), timeout=5) as response:
                    direct_statuses.append(response.status)
            except HTTPError as error:
                with error:
                    direct_statuses.append(error.code)
        expected = [200, 200]
        claim_summary["direct_statuses"] = direct_statuses
        self.assertEqual(browser_auth.get("statuses"), expected, claim_summary)
        self.assertEqual(direct_statuses, expected, claim_summary)

    def nav(self, label: str):
        self.wait.until(EC.element_to_be_clickable(
            (By.XPATH, f"//nav[@aria-label='Workspace sections']//button[contains(normalize-space(), '{label}')]"))).click()

    def assert_no_react_hook_order_error(self):
        messages = [entry.get("message", "") for entry in self.driver.get_log("browser")]
        self.assertFalse(any("Minified React error #310" in message for message in messages), messages)

    def test_local_admin_mobile_navigation_and_sign_out(self):
        self.driver.set_window_size(390, 844)
        self.login("admin", "ADMIN_PASSWORD")
        for section in ("Prices & coupons", "Inventory", "Catalog"):
            self.nav(section)
            self.wait.until(lambda driver: driver.find_element(By.TAG_NAME, "h1").text == f"{section}.")
        self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Sign out"]'))).click()
        self.wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(., 'Sign in with local account')]")))
        self.driver.refresh()
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '.login-shell')))
        self.assertFalse(self.driver.find_elements(By.CSS_SELECTOR, '.app-shell'))

    def test_catalog_login_products_art_and_product_creation(self):
        self.login("admin", "ADMIN_PASSWORD")
        self.assertEqual(self.driver.find_element(By.TAG_NAME, "h1").text, "Catalog.")
        for title in ("Pro Willow Cricket Bat", "Control Match Football"):
            self.wait.until(EC.visibility_of_element_located(
                (By.XPATH, f"//article[contains(@class,'product-card')]//h2[normalize-space()='{title}']")))
        self.assertGreaterEqual(len(self.driver.find_elements(By.CSS_SELECTOR, ".product-card")), 6)
        image_widths = self.driver.execute_script(
            "return Array.from(document.querySelectorAll('.product-card img')).map(image => image.naturalWidth)")
        self.assertTrue(image_widths and all(width > 0 for width in image_widths), image_widths)
        self.assertGreater(self.driver.execute_script(
            "return document.querySelector('.brand-link img').naturalWidth"), 0)
        cricket_filter = self.driver.find_element(
            By.XPATH, "//div[contains(@class,'filter-pills')]//button[contains(., 'Cricket')]")
        cricket_filter.click()
        self.wait.until(lambda driver: all(
            "Football" not in card.text for card in driver.find_elements(By.CSS_SELECTOR, ".product-card")))
        self.assertTrue(any("Pro Willow Cricket Bat" in card.text
                            for card in self.driver.find_elements(By.CSS_SELECTOR, ".product-card")))
        self.driver.find_element(By.XPATH,
            "//div[contains(@class,'filter-pills')]//button[normalize-space()='All sports']").click()
        self.wait.until(lambda driver: len(driver.find_elements(By.CSS_SELECTOR, ".product-card")) >= 6)

        existing = self.driver.find_elements(By.XPATH,
            f"//article[contains(@class,'product-card')][.//h2[normalize-space()='{TEST_PRODUCT_TITLE}']]")
        is_live = bool(existing and existing[0].find_element(By.CSS_SELECTOR, ".stock-tag").text == "LIVE")
        if not is_live:
            self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(., 'Add product')]"))).click()
            self.wait.until(EC.visibility_of_element_located((By.NAME, "title"))).send_keys(TEST_PRODUCT_TITLE)
            self.driver.find_element(By.NAME, "brand").send_keys("SuperSports Test Lab")
            self.driver.find_element(By.NAME, "slug").send_keys(TEST_PRODUCT_SLUG)
            category = Select(self.driver.find_element(By.NAME, "category"))
            category.select_by_index(1)
            self.driver.find_element(By.NAME, "code").send_keys(TEST_SKU_CODE)
            self.driver.find_element(By.NAME, "asset").send_keys("products/cricket-bat.svg")
            self.driver.find_element(By.NAME, "alt").send_keys("Selenium regression product artwork")
            self.driver.find_element(By.NAME, "inr").send_keys("129900")
            self.driver.find_element(By.NAME, "usd").send_keys("1599")
            self.driver.find_element(By.CSS_SELECTOR, "textarea[name='description']").send_keys(
                "Synthetic product created once by the repeatable Selenium UI suite.")
            self.driver.find_element(By.XPATH, "//button[normalize-space()='Save and activate']").click()
            result = self.wait.until(lambda driver: (
                "saved" if driver.find_elements(By.CSS_SELECTOR, '[role="status"]')
                else ("error", driver.find_element(By.CSS_SELECTOR, '[role="alert"]').text)
                if driver.find_elements(By.CSS_SELECTOR, '[role="alert"]') else False
            ))
            if result != "saved":
                self.fail(f"Product save failed in the UI: {result[1]}")

        product_card = self.wait.until(EC.visibility_of_element_located(
            (By.XPATH, f"//article[contains(@class,'product-card')][.//h2[normalize-space()='{TEST_PRODUCT_TITLE}']]")))
        self.assertEqual(product_card.find_element(By.CSS_SELECTOR, ".stock-tag").text, "LIVE")
        self.assert_no_react_hook_order_error()

    def test_pricing_currency_books_coupon_list_and_coupon_creation(self):
        self.login("admin", "ADMIN_PASSWORD")
        self.nav("Prices & coupons")
        self.wait.until(EC.visibility_of_element_located(
            (By.XPATH, "//h2[normalize-space()='Products & pricing']")))
        price_table = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".section-block .table-wrap")))
        self.assertIn("SS-CR-BAT-001", price_table.text)
        expected_coupons = {"WELCOME10", "CRICKET250"}
        coupon_codes = lambda driver: {element.text for element in
            driver.find_elements(By.CSS_SELECTOR, ".coupon-card code")}
        self.wait.until(lambda driver: expected_coupons.issubset(coupon_codes(driver)) or
                        driver.find_elements(By.CSS_SELECTOR, '[role="alert"]'))
        self.assertTrue(expected_coupons.issubset(coupon_codes(self.driver)),
                        f"Fixture coupons missing; alert={self.driver.find_elements(By.CSS_SELECTOR, '[role=\"alert\"]') and self.driver.find_element(By.CSS_SELECTOR, '[role=\"alert\"]').text}; page={self.driver.find_element(By.CSS_SELECTOR, '.content').text}")

        currency_buttons = self.driver.find_elements(By.CSS_SELECTOR, ".currency-switch button")
        original_currency = next(button.text.split()[-1] for button in currency_buttons
                                 if button.get_attribute("aria-pressed") == "true")
        other_currency = "USD" if original_currency == "INR" else "INR"
        try:
            self.driver.find_element(By.XPATH,
                f"//div[contains(@class,'currency-switch')]//button[contains(., '{other_currency}')]").click()
            self.wait.until(lambda driver: any(
                button.get_attribute("aria-pressed") == "true" and other_currency in button.text
                for button in driver.find_elements(By.CSS_SELECTOR, ".currency-switch button")))
        finally:
            if other_currency != original_currency:
                self.driver.find_element(By.XPATH,
                    f"//div[contains(@class,'currency-switch')]//button[contains(., '{original_currency}')]").click()
                self.wait.until(lambda driver: any(
                    button.get_attribute("aria-pressed") == "true" and original_currency in button.text
                    for button in driver.find_elements(By.CSS_SELECTOR, ".currency-switch button")))

        coupon_exists = self.driver.find_elements(By.XPATH,
            f"//article[contains(@class,'coupon-card')]//code[normalize-space()='{TEST_COUPON_CODE}']")
        if not coupon_exists:
            self.driver.find_element(By.XPATH, "//button[contains(., 'Create coupon')]").click()
            form = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "form.coupon-form")))
            form.find_element(By.NAME, "code").send_keys(TEST_COUPON_CODE)
            form.find_element(By.NAME, "value").send_keys("1000")
            now = datetime.now().replace(second=0, microsecond=0)
            starts = (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M")
            ends = (now + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M")
            for field_name, value in (("startsAt", starts), ("endsAt", ends)):
                field = form.find_element(By.NAME, field_name)
                self.driver.execute_script("""
                    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
                    setter.call(arguments[0], arguments[1]);
                    arguments[0].dispatchEvent(new Event('input', {bubbles:true}));
                    arguments[0].dispatchEvent(new Event('change', {bubbles:true}));
                """, field, value)
            validation = self.driver.execute_script("""
                return Array.from(arguments[0].elements)
                  .filter((field) => field.willValidate && !field.validity.valid)
                  .map((field) => ({name: field.name, message: field.validationMessage}))
            """, form)
            self.assertEqual(validation, [], f"Coupon form fields are invalid: {validation}")
            form.find_element(By.XPATH, ".//button[normalize-space()='Save coupon']").click()

        outcome = self.wait.until(lambda driver: (
            "saved" if driver.find_elements(By.XPATH,
                f"//article[contains(@class,'coupon-card')]//code[normalize-space()='{TEST_COUPON_CODE}']")
            else ("error", driver.find_element(By.CSS_SELECTOR, '[role="alert"]').text)
            if driver.find_elements(By.CSS_SELECTOR, '[role="alert"]') else False
        ))
        if outcome != "saved":
            self.fail(f"Coupon save failed in the UI: {outcome[1]}")
        self.assert_no_react_hook_order_error()

    def test_inventory_adjustment_replay_and_reversal(self):
        self.login("admin", "ADMIN_PASSWORD")
        self.nav("Inventory")
        self.wait.until(EC.visibility_of_element_located(
            (By.XPATH, "//h2[normalize-space()='Warehouse stock']")))
        row_for_bat = lambda driver: next((row for row in driver.find_elements(By.CSS_SELECTOR, "tbody tr")
                                           if "SS-CR-BAT-001" in row.text), False)
        try:
            row = self.wait.until(row_for_bat)
        except TimeoutException:
            alerts = [item.text for item in self.driver.find_elements(By.CSS_SELECTOR, '[role="alert"]')]
            self.fail(f"Inventory balances did not render; alerts={alerts}; view={self.driver.find_element(By.CSS_SELECTOR, '.content').text}")
        original = int(row.find_element(By.CSS_SELECTOR, ".quantity-cell").text)
        sku_select = Select(self.driver.find_element(By.NAME, "skuId"))
        option = next(option for option in sku_select.options if "SS-CR-BAT-001" in option.text)
        sku_id = option.get_attribute("value")
        suffix = uuid.uuid4().hex[:12]
        first_key = f"selenium-ui-{suffix}"
        reverse_key = f"selenium-ui-reverse-{suffix}"
        changed = False

        def submit_adjustment(delta: int, key: str):
            Select(self.driver.find_element(By.NAME, "skuId")).select_by_value(sku_id)
            quantity = self.driver.find_element(By.NAME, "delta")
            quantity.clear()
            quantity.send_keys(str(delta))
            self.driver.find_element(By.NAME, "reason").send_keys("Selenium UI regression adjustment")
            self.driver.find_element(By.NAME, "key").send_keys(key)
            self.driver.find_element(By.XPATH,
                "//button[contains(., 'Save stock movement')]").click()

        def quantity_now() -> int:
            current = row_for_bat(self.driver)
            return int(current.find_element(By.CSS_SELECTOR, ".quantity-cell").text)

        try:
            submit_adjustment(1, first_key)
            self.wait.until(lambda _: quantity_now() == original + 1)
            changed = True

            submit_adjustment(1, first_key)
            self.wait.until(lambda _: quantity_now() == original + 1)

            submit_adjustment(-1, reverse_key)
            self.wait.until(lambda _: quantity_now() == original)
            changed = False
        finally:
            if changed:
                submit_adjustment(-1, reverse_key)
                try:
                    self.wait.until(lambda _: quantity_now() == original)
                except TimeoutException:
                    pass

        self.assert_no_react_hook_order_error()


if __name__ == "__main__":
    unittest.main(verbosity=2)
