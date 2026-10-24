import unittest
from unittest.mock import patch

import app


class GraphProjectionTest(unittest.TestCase):
    def test_ignores_non_order_lifecycle_events(self):
        with patch.object(app.driver, "session") as session:
            app.project_event({"eventType": "OrderCancelled", "data": {}})
            session.assert_not_called()

    def test_rejects_oversized_order_line_projection(self):
        event = {"eventType": "OrderAccepted", "data": {"lines": [{}] * 101}}
        with self.assertRaisesRegex(ValueError, "bounds"):
            app.project_event(event)


if __name__ == "__main__":
    unittest.main()
