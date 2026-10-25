import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import checkout_burst


class CheckoutBurstTests(unittest.TestCase):
    def test_percentile_uses_nearest_rank(self):
        self.assertEqual(checkout_burst.percentile([10, 20, 30, 40], 0.50), 20)
        self.assertEqual(checkout_burst.percentile([10, 20, 30, 40], 0.95), 40)

    def test_percentile_is_empty_for_no_samples(self):
        self.assertIsNone(checkout_burst.percentile([], 0.95))

    def test_probe_rejects_unbounded_or_invalid_worker_counts_before_preflight(self):
        for orders, workers in ((0, 1), (51, 1), (4, 0), (4, 5), (51, 17)):
            with self.subTest(orders=orders, workers=workers):
                with self.assertRaises(checkout_burst.ProbeFailure):
                    checkout_burst.run_probe(orders, workers, "supersports")


if __name__ == "__main__":
    unittest.main()
