"""Selenium smoke checks for the optional local Grafana operations dashboard."""
import os
import unittest

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

M09_LIVE = os.getenv("SUPERSPORTS_M09_LIVE_ACCEPTANCE") == "true"


@unittest.skipUnless(M09_LIVE, "Run only after starting the isolated M09 observability profile.")
class OperationsDashboardUiTests(unittest.TestCase):
    def test_grafana_shows_provisioned_supersports_health_dashboard(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1440,1000")
        driver = webdriver.Chrome(options=options)
        self.addCleanup(driver.quit)
        wait = WebDriverWait(driver, 30)
        driver.get(os.getenv("SUPERSPORTS_GRAFANA_URL", "http://localhost:3001"))
        wait.until(EC.presence_of_element_located((By.NAME, "user"))).send_keys("admin")
        driver.find_element(By.NAME, "password").send_keys("admin\n")
        # A persisted local Grafana volume may retain the first-run password
        # prompt even though the configured demo credentials authenticate.
        try:
            skip = WebDriverWait(driver, 5).until(EC.element_to_be_clickable(
                (By.XPATH, "//button[normalize-space()='Skip'] | //a[normalize-space()='Skip']")))
            skip.click()
        except Exception:
            pass
        driver.get(os.getenv("SUPERSPORTS_GRAFANA_URL", "http://localhost:3001")+
                   "/d/supersports-service-health/supersports-local-service-health")
        wait.until(EC.visibility_of_element_located((By.XPATH, "//*[contains(., 'SuperSports local service health')]")))
        self.assertIn("Readiness by service", driver.find_element(By.TAG_NAME, "body").text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
