"""Selenium browser check for the local Kafka inspector."""
import os
import unittest
from urllib.error import URLError
from urllib.request import urlopen

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

BASE = os.environ.get("KAFKA_UI_URL", "http://localhost:8091")


@unittest.skipUnless(os.environ.get("SUPERSPORTS_KAFKA_UI_BROWSER") == "1", "Enable for a running Kafka UI browser check")
class KafkaUiBrowserTests(unittest.TestCase):
    def test_cluster_overview_renders_for_host_browser(self):
        with urlopen(BASE + "/actuator/health", timeout=5) as response:
            if response.status != 200:
                self.skipTest("Kafka UI is not running")
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1440,1000")
        options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=options)
        self.addCleanup(driver.quit)
        driver.get(BASE)
        wait = WebDriverWait(driver, 30)
        wait.until(EC.presence_of_element_located((By.NAME, "username"))).send_keys("admin")
        driver.find_element(By.NAME, "password").send_keys("admin\n")
        WebDriverWait(driver, 20).until(lambda browser: "supersports" in browser.page_source.lower())
        self.assertIn("supersports", driver.page_source.lower())


if __name__ == "__main__":
    unittest.main()
