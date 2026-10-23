"""Real Docker/PostgreSQL/Keycloak regressions, run by supersports test."""
import json
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "devops/scripts"))
import manage

CATALOG = "http://127.0.0.1:8081"
CONFIGURATION = "http://127.0.0.1:8082"


@unittest.skipUnless(os.environ.get("SUPERSPORTS_INTEGRATION") == "1",
                     "Run through devops/scripts/supersports test against the local core profile.")
class CoreIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project = manage.validated_project_name(os.environ.get("SUPERSPORTS_PROJECT", "supersports"))
        cls.credentials = manage.load_credentials(ROOT / "devops/.local/bootstrap.env")
        cls.customer = manage.token_for("customer", cls.credentials["DEMO_CUSTOMER_PASSWORD"])
        cls.admin = manage.token_for("platform-admin", cls.credentials["DEMO_PLATFORM_ADMIN_PASSWORD"])
        cls.catalog_admin = manage.token_for("catalog-admin", cls.credentials["DEMO_CATALOG_ADMIN_PASSWORD"])
        cls.wrong_audience = manage.token_for("customer", cls.credentials["DEMO_CUSTOMER_PASSWORD"],
                                       "supersports-other-cli")

    def test_public_health_is_up_without_sensitive_details(self):
        for base in (CATALOG, CONFIGURATION):
            for probe in ("liveness", "readiness"):
                with self.subTest(base=base, probe=probe):
                    status, body = manage.request_json(f"{base}/actuator/health/{probe}")
                    self.assertEqual(status, 200)
                    self.assertEqual(body, {"status": "UP"})

    def test_anonymous_api_access_is_unauthorized(self):
        for url in (f"{CATALOG}/api/v1/catalog/status",
                    f"{CONFIGURATION}/api/v1/configuration"):
            self.assertEqual(manage.request_json(url)[0], 401)

    def test_customer_and_catalog_admin_can_read_catalog_status(self):
        for token in (self.customer, self.catalog_admin):
            status, body = manage.request_json(f"{CATALOG}/api/v1/catalog/status", token=token)
            self.assertEqual(status, 200)
            self.assertEqual(body, {"service": "catalog", "status": "ready", "schemaVersion": 1})

    def test_customer_and_catalog_admin_cannot_read_platform_configuration(self):
        for token in (self.customer, self.catalog_admin):
            self.assertEqual(manage.request_json(f"{CONFIGURATION}/api/v1/configuration", token=token)[0], 403)

    def test_platform_configuration_has_categorized_non_secret_defaults(self):
        status, body = manage.request_json(f"{CONFIGURATION}/api/v1/configuration", token=self.admin)
        self.assertEqual(status, 200)
        self.assertEqual(body["revision"], 1)
        categories = {item["id"] for item in body["categories"]}
        self.assertEqual(categories, {
            "store-localization", "commerce-simulations", "storage", "search-cache",
            "messaging-workflows", "identity-access", "observability", "nova-models",
        })
        settings = {item["key"]: item for item in body["settings"]}
        self.assertEqual(settings["store.currency"]["value"], "INR")
        self.assertEqual(settings["store.country"]["value"], "IN")
        self.assertEqual(settings["store.language"]["value"], "en")
        for item in settings.values():
            self.assertIn(item["category"], categories)
            self.assertIn(item["valueType"], {"STRING", "STRING_LIST", "BOOLEAN"})
            self.assertEqual(item["activationMode"], "MIGRATION_ONLY")
        rendered = json.dumps(body)
        self.assertTrue(all(secret not in rendered for secret in self.credentials.values()))

    def test_authenticated_mutation_methods_do_not_change_configuration(self):
        url = f"{CONFIGURATION}/api/v1/configuration"
        before = manage.request_json(url, token=self.admin)
        self.assertEqual(before[0], 200)
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            status, _ = manage.request_json(url, token=self.admin, method=method,
                                            data=b'{"store.currency":"USD"}')
            self.assertIn(status, (401, 403, 405), method)
            self.assertEqual(manage.request_json(url, token=self.admin), before, method)

    def test_wrong_audience_and_tampered_tokens_are_rejected(self):
        for token in (self.wrong_audience, self.customer[:-8] + "tampered"):
            for url in (f"{CATALOG}/api/v1/catalog/status",
                        f"{CONFIGURATION}/api/v1/configuration"):
                self.assertEqual(manage.request_json(url, token=token)[0], 401)

    def test_other_actuator_endpoints_are_not_exposed(self):
        self.assertIn(manage.request_json(f"{CATALOG}/actuator/env", token=self.customer)[0], (403, 404))

    def test_identity_discovery_advertises_exact_public_issuer(self):
        status, body = manage.request_json(
            "http://127.0.0.1:8180/realms/supersports/.well-known/openid-configuration")
        self.assertEqual(status, 200)
        self.assertEqual(body["issuer"], "http://localhost:8180/realms/supersports")

    def psql(self, role, database, sql):
        keys = {"catalog": "CATALOG_DB_PASSWORD",
                "configuration": "CONFIGURATION_DB_PASSWORD"}
        command = ('export PGPASSWORD="$' + keys[role] + '"; exec psql -X -A -t '
                   f'-h 127.0.0.1 -U supersports_{role} -d {database} -c \'{sql}\'')
        return manage.compose(["exec", "-T", "postgres", "sh", "-ec", command],
                              project=self.project, capture=True, check=False)

    def test_each_service_can_connect_to_its_own_migrated_database(self):
        for service in ("catalog", "configuration"):
            result = self.psql(service, service,
                               "SELECT count(*) FROM flyway_schema_history WHERE success")
            self.assertEqual(result.returncode, 0)
            self.assertGreaterEqual(int(result.stdout.strip()), 1)

    def test_service_database_roles_cannot_connect_to_each_other_database(self):
        for owner, other in (("catalog", "configuration"), ("configuration", "catalog")):
            result = self.psql(owner, other, "SELECT 1")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("permission denied", result.stderr.lower())

    def test_postgres_has_no_host_port_and_apps_bind_only_to_loopback(self):
        result = manage.compose(["ps", "--format", "json"], project=self.project, capture=True)
        # Compose emits one JSON object per line for multiple services.
        rows = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
        self.assertEqual({row["Service"] for row in rows}, {"postgres", "identity", "catalog", "configuration"})
        for row in rows:
            publishers = row.get("Publishers") or []
            if row["Service"] == "postgres":
                self.assertFalse(any(port.get("PublishedPort", 0) for port in publishers))
            else:
                self.assertTrue(publishers)
                for port in publishers:
                    if port.get("PublishedPort", 0):
                        self.assertEqual(port["URL"], "127.0.0.1")


if __name__ == "__main__":
    unittest.main()
