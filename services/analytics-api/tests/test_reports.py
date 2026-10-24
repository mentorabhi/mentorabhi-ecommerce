import unittest
from unittest.mock import patch

from fastapi import HTTPException
import app


class ReportsTest(unittest.TestCase):
    def test_currency_is_a_strict_iso_code_before_sql(self):
        with self.assertRaises(HTTPException) as caught:
            app.query("SELECT 1 WHERE currency=?", "INR' OR 1=1 --")
        self.assertEqual(caught.exception.status_code, 422)

    def test_period_and_row_bounds_are_enforced_before_connecting(self):
        for kwargs in ({"days": 6}, {"days": 366}, {"limit": 0}, {"limit": 101}):
            with self.subTest(kwargs=kwargs), self.assertRaises(HTTPException) as caught:
                app.query("SELECT 1", "INR", **kwargs)
            self.assertEqual(caught.exception.status_code, 422)

    @patch("app.connect")
    def test_query_uses_validated_period_and_limit_values(self, connect):
        cursor = connect.return_value.cursor.return_value
        cursor.description = [("day",)]
        cursor.fetchall.return_value = []
        app.query("SELECT * FROM reports WHERE currency=? AND day >= current_timestamp - INTERVAL '$DAYS' DAY LIMIT $LIMIT",
                  "USD", days=90, limit=25)
        cursor.execute.assert_called_once_with(
            "SELECT * FROM reports WHERE currency='USD' AND day >= current_timestamp - INTERVAL '90' DAY LIMIT 25")

    @patch("app.query", return_value=[{"confirmed_orders": 0}])
    def test_summary_threads_selected_currency_and_period_to_all_commerce_measures(self, query):
        self.assertEqual(app.summary("INR", 90), {"confirmed_orders": 0})
        sql, currency = query.call_args.args
        self.assertEqual(currency, "INR")
        self.assertEqual(query.call_args.kwargs["days"], 90)
        self.assertIn("subtotalMinor", sql)
        self.assertIn("order_lines", sql)
        self.assertIn("OrderReturnRequested", sql)

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
