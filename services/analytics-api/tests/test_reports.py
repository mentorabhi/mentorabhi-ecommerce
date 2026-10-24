import unittest
from unittest.mock import patch

from fastapi import HTTPException
import app


class ReportsTest(unittest.TestCase):
    def test_currency_is_a_strict_iso_code_before_sql(self):
        with self.assertRaises(HTTPException) as caught:
            app.query("SELECT 1 WHERE currency=?", "INR' OR 1=1 --")
        self.assertEqual(caught.exception.status_code, 422)

    @patch("app.connect")
    def test_summary_uses_only_allowlisted_read_query(self, connect):
        cursor = connect.return_value.cursor.return_value
        cursor.description = [("confirmed_orders",), ("gross_sales_minor",)]
        cursor.fetchall.return_value = [(2, 15000)]
        result = app.query("SELECT COUNT(*) AS confirmed_orders WHERE currency=?", "INR")
        self.assertEqual(result, [{"confirmed_orders": 2, "gross_sales_minor": 15000}])
        connect.assert_called_once()
        cursor.execute.assert_called_once_with("SELECT COUNT(*) AS confirmed_orders WHERE currency='INR'")


if __name__ == "__main__":
    unittest.main()
