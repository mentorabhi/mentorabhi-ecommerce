"""Opt-in browser acceptance for enabled local operations interfaces."""
import os
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import base64

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


@unittest.skipUnless(os.getenv("SUPERSPORTS_OPERATIONS_UI") == "1", "Enable with operations profiles running")
class OperationalUiTests(unittest.TestCase):
    def setUp(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1440,1100")
        self.driver = webdriver.Chrome(options=options)
        self.addCleanup(self.driver.quit)
        self.wait = WebDriverWait(self.driver, 30)

    def test_keycloak_master_console_accepts_demo_admin(self):
        self.driver.get("http://localhost:8180/admin/master/console/")
        self.wait.until(EC.presence_of_element_located((By.NAME, "username"))).send_keys("admin")
        self.driver.find_element(By.NAME, "password").send_keys("admin\n")
        self.wait.until(EC.visibility_of_element_located((By.LINK_TEXT, "Clients")))
        self.assertIn("/admin/master/console", self.driver.current_url)

    @unittest.skipUnless(os.getenv("SUPERSPORTS_NEO4J_UI") == "1", "Enable for the graph profile")
    def test_neo4j_browser_accepts_demo_admin(self):
        self.driver.get("http://localhost:7474/browser/")
        hostname = self.wait.until(EC.presence_of_element_located((By.NAME, "hostname")))
        hostname.clear()
        hostname.send_keys("localhost:7687")
        username = self.driver.find_element(By.NAME, "username")
        username.clear()
        username.send_keys("admin")
        self.driver.find_element(By.NAME, "password").send_keys("admin")
        self.driver.find_element(By.XPATH, "//button[normalize-space()='Connect']").click()
        self.wait.until(lambda driver: "User:\nadmin" in driver.find_element(By.TAG_NAME, "body").text)

    @unittest.skipUnless(os.getenv("SUPERSPORTS_SUPERSET_UI") == "1", "Enable for the dashboard studio profile")
    def test_superset_accepts_demo_admin(self):
        self.driver.get("http://localhost:8095/login/")
        self.wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys("admin")
        self.driver.find_element(By.ID, "password").send_keys("admin\n")
        self.wait.until(lambda driver: "/login" not in driver.current_url)
        self.wait.until(lambda driver: "Dashboards" in driver.find_element(By.TAG_NAME, "body").text)

    def test_prometheus_and_trino_require_password_and_render(self):
        for port, path, text in ((9090, "/query", "Prometheus"), (8096, "/ui/", "Trino")):
            with self.subTest(port=port):
                url = f"http://localhost:{port}{path}"
                for credential in (None, "admin:wrong"):
                    headers = {} if credential is None else {"Authorization": "Basic " + base64.b64encode(credential.encode()).decode()}
                    with self.assertRaises(HTTPError) as failed:
                        urlopen(Request(url, headers=headers), timeout=10)
                    self.assertEqual(failed.exception.code, 401)
                    failed.exception.close()
                self.driver.get(f"http://admin:admin@localhost:{port}{path}")
                if port == 8096:
                    self.wait.until(EC.visibility_of_element_located((By.ID, "usernameInput"))).send_keys("admin\n")
                    self.wait.until(EC.invisibility_of_element_located((By.ID, "usernameInput")))
                    self.wait.until(lambda driver: "Query" in driver.find_element(By.TAG_NAME, "body").text)
                else:
                    self.wait.until(lambda driver: text.lower() in driver.find_element(By.TAG_NAME, "body").text.lower())
                self.assertNotIn("401 Authorization Required", self.driver.page_source)
