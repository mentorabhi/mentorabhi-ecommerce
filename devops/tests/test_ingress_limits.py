"""Opt-in live test source for bounded Nginx ingress, never run in this phase."""
import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError
from urllib.request import Request, urlopen


@unittest.skipUnless(os.getenv("SUPERSPORTS_M09_LIVE_ACCEPTANCE") == "true",
                     "Run only in the explicit isolated M09 acceptance pass.")
class IngressLimitsTest(unittest.TestCase):
    def test_rate_limit_returns_429_and_normal_health_remains_available(self):
        def request(_):
            try:
                with urlopen("http://localhost:3000/api/catalog/categories", timeout=2) as response:
                    return response.status
            except HTTPError as error:
                with error:
                    return error.code
        with ThreadPoolExecutor(max_workers=24) as executor:
            statuses = list(executor.map(request,range(400)))
        self.assertIn(429, statuses)
        with urlopen("http://localhost:3000/healthz", timeout=2) as response:
            self.assertEqual(response.status, 200)

    def test_oversized_body_is_rejected(self):
        request = Request("http://localhost:3000/api/catalog/admin/products", data=b"x" * (1024 * 1024 + 1), method="POST")
        with self.assertRaises(HTTPError) as error:
            urlopen(request, timeout=3)
        self.assertEqual(error.exception.code, 413)


if __name__ == "__main__":
    unittest.main(verbosity=2)
