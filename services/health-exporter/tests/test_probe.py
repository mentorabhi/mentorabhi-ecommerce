import unittest
from unittest.mock import patch

import app


class ProbeTest(unittest.TestCase):
    def test_tcp_reachable_target_is_up(self):
        with patch("app.socket.create_connection"):
            name, up, elapsed = app.probe({"name": "db", "url": "tcp://postgres:5432"})
        self.assertEqual((name, up), ("db", 1))
        self.assertGreaterEqual(elapsed, 0)

    def test_unreachable_target_is_down_without_leaking_error(self):
        with patch("app.socket.create_connection", side_effect=OSError("secret-ish detail")):
            name, up, _ = app.probe({"name": "db", "url": "tcp://postgres:5432"})
        self.assertEqual((name, up), ("db", 0))


if __name__ == "__main__":
    unittest.main()
