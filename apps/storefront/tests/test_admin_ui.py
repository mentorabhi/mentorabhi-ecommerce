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
        self.driver.get(BASE_URL + "/admin")
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
        for section in ("Prices & coupons", "Inventory", "Shipments", "Reviews", "Support", "Catalog"):
            self.nav(section)
            self.wait.until(lambda driver: driver.find_element(By.TAG_NAME, "h1").text == f"{section}.")
        self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Sign out"]'))).click()
        self.wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(., 'Sign in with local account')]")))
        self.driver.refresh()
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '.login-shell')))
        self.assertFalse(self.driver.find_elements(By.CSS_SELECTOR, '.app-shell'))

    def test_operator_advances_a_prepared_synthetic_shipment(self):
        order_id=os.environ.get("SUPERSPORTS_SCHEDULED_ORDER_ID")
        if not order_id:self.skipTest("Set SUPERSPORTS_SCHEDULED_ORDER_ID to a prepared scheduled shipment.")
        self.login("admin","ADMIN_PASSWORD");self.nav("Shipments")
        self.driver.find_element(By.CSS_SELECTOR,"input[placeholder='Paste a scheduled order UUID']").send_keys(order_id)
        self.driver.find_element(By.XPATH,"//button[normalize-space()='Load shipment']").click()
        self.wait.until(EC.visibility_of_element_located((By.XPATH,"//*[contains(.,'SCHEDULED')]")))
        self.wait.until(EC.element_to_be_clickable((By.XPATH,"//button[normalize-space()='Advance to HANDED_OFF']"))).click()
        self.wait.until(EC.visibility_of_element_located((By.XPATH,"//*[contains(.,'HANDED_OFF')]")))

    def test_checkout_configuration_categories_update_and_audit_feedback(self):
        self.login("admin", "ADMIN_PASSWORD")
        self.nav("Configuration")
        self.wait.until(lambda driver: driver.find_element(By.TAG_NAME, "h1").text == "Configuration.")
        row_selector = "//article[contains(@class,'configuration-row')][.//code[normalize-space()='checkout.tax.rate-bps']]"
        row = self.wait.until(EC.visibility_of_element_located((By.XPATH, row_selector)))
        changed = "1900" if row.find_element(By.NAME, "value").get_attribute("value") != "1900" else "1700"
        section_selector = "//section[contains(@class,'section-block')][.//code[normalize-space()='checkout.tax.rate-bps']]"
        def revision():
            text = self.driver.find_element(By.XPATH, section_selector).find_element(By.CSS_SELECTOR, ".result-count").text
            return int(text.split()[-1])
        def save_tax(value, after_revision):
            current = self.driver.find_element(By.XPATH, row_selector)
            field = current.find_element(By.NAME, "value"); field.clear(); field.send_keys(value)
            current.find_element(By.XPATH, ".//button[normalize-space()='Save']").click()
            self.wait.until(lambda _driver: revision() > after_revision)
            self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".notice.success")))
        try:
            save_tax(changed, revision())
            self.assertIn("updated and recorded in the audit log", self.driver.find_element(By.CSS_SELECTOR, ".notice.success").text)
        finally:
            save_tax("1800", revision())
        self.assertEqual(self.driver.find_element(By.XPATH, row_selector).find_element(By.NAME, "value").get_attribute("value"), "1800")
        self.assertIn("Commerce simulations", self.driver.find_element(By.CSS_SELECTOR, ".configuration-groups").text)
        return_row="//article[contains(@class,'configuration-row')][.//code[normalize-space()='returns.window-days']]"
        self.wait.until(EC.visibility_of_element_located((By.XPATH,return_row)))
        self.assertIn("Returns policy",self.driver.find_element(By.CSS_SELECTOR,".configuration-groups").text)
        return_field=self.driver.find_element(By.XPATH,return_row).find_element(By.NAME,"value")
        prior=return_field.get_attribute("value");changed_window="21" if prior!="21" else "28"
        def save_window(value):
            current=self.driver.find_element(By.XPATH,return_row);field=current.find_element(By.NAME,"value");field.clear();field.send_keys(value)
            current.find_element(By.XPATH,".//button[normalize-space()='Save']").click()
            self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR,".notice.success")))
            self.wait.until(lambda _driver:self.driver.find_element(By.XPATH,return_row).find_element(By.NAME,"value").get_attribute("value")==value)
        try:save_window(changed_window)
        finally:save_window(prior)
        self.assert_no_react_hook_order_error()

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

    def test_return_inspection_operator_queue_when_fixture_is_provided(self):
        return_id = os.environ.get("SUPERSPORTS_INSPECTABLE_RETURN_ID")
        if not return_id:
            self.skipTest("Set SUPERSPORTS_INSPECTABLE_RETURN_ID to a refunded return awaiting inspection.")
        self.login("admin", "ADMIN_PASSWORD")
        self.nav("Inventory")
        receipt = self.wait.until(EC.visibility_of_element_located(
            (By.XPATH, f"//article[contains(@class,'section-block')][.//span[contains(.,'{return_id}')]]")))
        selects = receipt.find_elements(By.CSS_SELECTOR, "select")
        reasons = receipt.find_elements(By.CSS_SELECTOR, "input[maxlength='500']")
        self.assertTrue(selects)
        self.assertEqual(len(selects), len(reasons))
        for selector, reason in zip(selects, reasons):
            Select(selector).select_by_value("SELLABLE")
            reason.send_keys("Selenium fixture item inspected")
        receipt.find_element(By.XPATH, ".//button[normalize-space()='Save inspection decisions']").click()
        self.wait.until(EC.invisibility_of_element_located(
            (By.XPATH, f"//article[contains(@class,'section-block')][.//span[contains(.,'{return_id}')]]")))
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

    def register_customer(self, username: str, email: str):
        password = f"SS-{uuid.uuid4().hex}Aa!"
        self.driver.get(BASE_URL + "/account")
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".profile-prompt")))
        self.wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(., 'Sign in or create account')]"))).click()
        self.wait.until(lambda driver: "/realms/supersports-customers/" in driver.current_url)
        self.wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Register"))).click()
        for name, value in (("firstName", "UI"), ("lastName", "Customer"), ("email", email), ("username", username)):
            self.wait.until(EC.presence_of_element_located((By.NAME, name))).send_keys(value)
        self.driver.find_element(By.NAME, "password").send_keys(password)
        self.driver.find_element(By.NAME, "password-confirm").send_keys(password)
        self.driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".shop-shell")))

    def test_customer_self_registration_browse_profile_cart_and_isolation(self):
        suffix = uuid.uuid4().hex[:10]
        first = f"shopper-{suffix}"
        self.driver.get(BASE_URL)
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".store-product-grid")))
        self.assertGreaterEqual(len(self.driver.find_elements(By.CSS_SELECTOR, ".store-card")), 6)
        self.driver.find_element(By.ID, "store-search").send_keys("football")
        self.driver.find_element(By.ID, "store-search").send_keys(Keys.ENTER)
        self.wait.until(lambda driver: driver.find_element(By.CSS_SELECTOR, ".collection-heading h1").text == 'Results for “football”')
        self.wait.until(lambda driver: len(driver.find_elements(By.CSS_SELECTOR, ".store-card")) == 3)

        self.register_customer(first, f"{first}@example.local")
        customer_auth = self.driver.execute_async_script("""
          const done=arguments[0];
          try {
            const stored=Object.values(sessionStorage).map(v=>{try{return JSON.parse(v)}catch{return null}}).find(v=>v&&v.access_token);
            if(!stored)return done({error:'customer token missing'});
            const payload=stored.access_token.split('.')[1];
            const claims=JSON.parse(atob(payload.replace(/-/g,'+').replace(/_/g,'/')+'='.repeat((4-payload.length%4)%4)));
            Promise.all(['/api/customer/profile','/api/catalog/admin/products','/api/pricing/coupons','/api/inventory/balances'].map(path=>
              fetch(path,{headers:{Authorization:`Bearer ${stored.access_token}`}}).then(response=>response.status)
            )).then(statuses=>done({iss:claims.iss,aud:claims.aud,statuses}));
          } catch(error){done({error:String(error)})}
        """)
        self.assertEqual(customer_auth.get("iss"), "http://localhost:8180/realms/supersports-customers", customer_auth)
        self.assertIn("supersports-customer-api", customer_auth.get("aud", []), customer_auth)
        self.assertNotIn("supersports-api", customer_auth.get("aud", []), customer_auth)
        self.assertEqual(customer_auth.get("statuses"), [200, 401, 401, 401], customer_auth)

        self.driver.get(BASE_URL)
        first_card = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".store-card-image")))
        first_card.click()
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".detail-layout")))
        self.driver.find_element(By.XPATH, "//button[contains(., 'Wishlist')]").click()
        self.wait.until(lambda driver: "Saved to your wishlist." in driver.find_element(By.CSS_SELECTOR, ".shop-shell").text)
        self.driver.find_element(By.XPATH, "//button[contains(., 'Add to cart')]").click()
        self.wait.until(lambda driver: "Added to your cart." in driver.find_element(By.CSS_SELECTOR, ".shop-shell").text or driver.find_elements(By.CSS_SELECTOR, ".store-alert.error"))
        self.assertIn("Added to your cart.", self.driver.find_element(By.CSS_SELECTOR, ".shop-shell").text)
        self.driver.find_element(By.XPATH, "//button[contains(., 'Add to cart')]").click()
        self.wait.until(lambda driver: "Added to your cart." in driver.find_element(By.CSS_SELECTOR, ".shop-shell").text)
        self.driver.find_element(By.CSS_SELECTOR, ".shop-actions a[href='/cart']").click()
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".saved-row")))
        self.assertIn("Your cart", self.driver.find_element(By.CSS_SELECTOR, ".customer-page").text)
        self.assertEqual(self.driver.find_element(By.CSS_SELECTOR, ".saved-row input[type='number']").get_attribute("value"), "2")

        self.driver.get(BASE_URL + "/account")
        fields = {"fullName": "UI Customer", "phone": "9876543210", "line1": "18 Race Course Road",
                  "line2": "", "city": "Bengaluru", "state": "Karnataka", "postalCode": "560001"}
        for name, value in fields.items():
            field = self.wait.until(EC.presence_of_element_located((By.NAME, name)))
            field.clear(); field.send_keys(value)
        self.driver.find_element(By.XPATH, "//button[contains(., 'Save profile and address')]").click()
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[role='status']")))
        search = self.driver.find_element(By.ID, "store-search")
        search.send_keys("football")
        search.send_keys(Keys.ENTER)
        self.wait.until(lambda driver: driver.find_element(By.CSS_SELECTOR, ".collection-heading h1").text == 'Results for “football”')
        self.wait.until(lambda driver: len(driver.find_elements(By.CSS_SELECTOR, ".store-card")) == 3)

        self.driver.get(BASE_URL + "/cart")
        self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Place simulated order')]"))).click()
        self.wait.until(lambda driver: driver.find_elements(By.CSS_SELECTOR, ".order-row") or driver.find_elements(By.CSS_SELECTOR, ".store-alert.error"))
        if not self.driver.find_elements(By.CSS_SELECTOR, ".order-row"):
            self.fail("Checkout UI returned an error: " + self.driver.find_element(By.CSS_SELECTOR, ".store-alert.error").text)
        self.assertIn("Order accepted for processing", self.driver.find_element(By.CSS_SELECTOR, ".shop-shell").text)
        self.assertTrue(self.driver.find_element(By.CSS_SELECTOR, ".order-row").find_element(By.TAG_NAME, "strong").text.startswith("Order "))
        self.driver.find_element(By.CSS_SELECTOR, ".order-row").click()
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".order-detail")))
        self.wait.until(lambda driver: "FULFILLMENT SCHEDULED" in driver.find_element(By.CSS_SELECTOR, ".order-detail").text.upper())
        self.assertIn("India", self.driver.find_element(By.CSS_SELECTOR, ".order-detail").text)
        self.assertIn("Simulated tax", self.driver.find_element(By.CSS_SELECTOR, ".order-detail").text)

        self.driver.get(BASE_URL + "/account")
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".address-form")))
        self.driver.find_element(By.XPATH, "//button[contains(., 'Sign out')]").click()
        self.wait.until(lambda driver: driver.current_url.rstrip("/") == BASE_URL)
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".shop-shell")))
        second = f"shopper-{uuid.uuid4().hex[:10]}"
        self.register_customer(second, f"{second}@example.local")
        self.driver.get(BASE_URL + "/cart")
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".customer-page")))
        self.assertFalse(self.driver.find_elements(By.CSS_SELECTOR, ".saved-row"), "Second customer inherited the first customer's cart")
        self.driver.get(BASE_URL + "/wishlist")
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".customer-page")))
        self.assertFalse(self.driver.find_elements(By.CSS_SELECTOR, ".store-card"), "Second customer inherited the first customer's wishlist")
        self.assert_no_react_hook_order_error()


    def test_analytics_dashboard_currency_and_report_widgets(self):
        self.login("catalog-admin", "DEMO_CATALOG_ADMIN_PASSWORD")
        self.wait.until(EC.element_to_be_clickable((By.XPATH, "//nav[@aria-label='Workspace sections']//button[contains(., 'Analytics')]"))).click()
        self.wait.until(EC.visibility_of_element_located((By.XPATH, "//h1[normalize-space()='Analytics']")))
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".metric-grid")))
        self.assertIn("Confirmed sales by day", self.driver.find_element(By.CSS_SELECTOR, ".analytics-dashboard").text)
        self.assertIn("Top products", self.driver.find_element(By.CSS_SELECTOR, ".analytics-dashboard").text)
        self.assertIn("Completed refund report", self.driver.find_element(By.CSS_SELECTOR, ".analytics-dashboard").text)
        self.driver.find_element(By.XPATH, "//button[normalize-space()='USD']").click()
        self.wait.until(lambda driver: "USD" in driver.find_element(By.CSS_SELECTOR, ".analytics-dashboard").text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
