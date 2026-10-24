"""Read-only, allowlisted reporting queries over local Trino."""
import re
from fastapi import FastAPI, HTTPException, Query
from trino.dbapi import connect

app = FastAPI(title="SuperSports analytics reports", version="1.0.0")


def query(sql: str, currency: str, *, days: int = 365, limit: int = 10):
    if not re.fullmatch(r"[A-Z]{3}", currency):
        raise HTTPException(422, "Currency must be a three-letter ISO code")
    connection = connect(host="trino", port=8080, user="supersports-reports",
                         catalog="lakehouse", schema="supersports", http_scheme="http")
    try:
        cursor = connection.cursor()
        cursor.execute(sql.replace("?", f"'{currency}'").replace("$DAYS", str(days)).replace("$LIMIT", str(limit)))
        names = [column[0] for column in cursor.description]
        return [dict(zip(names, row)) for row in cursor.fetchall()]
    except Exception as exc:
        raise HTTPException(503, "Analytics tables are not ready; run the local analytics job") from exc
    finally:
        connection.close()


@app.get("/health/ready")
def ready():
    return {"status": "UP", "dependency": "Trino is checked on report requests"}


@app.get("/api/reports/summary")
def summary(currency: str = Query("INR", min_length=3, max_length=3)):
    row = query("""WITH sales AS (
      SELECT COUNT(*) AS accepted_orders, COUNT_IF(confirmed) AS confirmed_orders,
             COALESCE(SUM(IF(confirmed,totalMinor,0)),0) AS gross_sales_minor,
             COALESCE(SUM(IF(confirmed,discountMinor,0)),0) AS discounts_minor
      FROM lakehouse.supersports.order_sales WHERE currency=?
    ), refunds AS (
      SELECT COALESCE(SUM(amountMinor),0) AS refunded_minor FROM lakehouse.supersports.order_refunds WHERE currency=?
    ), cancelled AS (
      SELECT COUNT(DISTINCT aggregateId) AS cancellations FROM lakehouse.supersports.raw_lifecycle
      WHERE eventType='OrderCancelled' AND json_extract_scalar(dataJson,'$.currency')=?
    ), returns AS (
      SELECT COUNT(DISTINCT r.aggregateId) AS return_orders FROM lakehouse.supersports.raw_lifecycle r
      JOIN lakehouse.supersports.order_sales s USING (aggregateId)
      WHERE r.eventType='OrderReturnRequested' AND s.currency=?
    ) SELECT * FROM sales CROSS JOIN refunds CROSS JOIN cancelled CROSS JOIN returns""", currency)
    return row[0] if row else {}


@app.get("/api/reports/daily-sales")
def daily_sales(currency: str = Query("INR", min_length=3, max_length=3), days: int = Query(30, ge=7, le=365)):
    return query("""SELECT CAST(occurredAt AS DATE) AS day, COUNT(*) AS orders,
      SUM(totalMinor) AS grossSalesMinor, SUM(discountMinor) AS discountsMinor
      FROM lakehouse.supersports.order_sales WHERE currency=? AND confirmed
      AND occurredAt >= current_timestamp - INTERVAL '$DAYS' DAY
      GROUP BY 1 ORDER BY 1 DESC LIMIT $DAYS""", currency, days=days)


@app.get("/api/reports/top-products")
def top_products(currency: str = Query("INR", min_length=3, max_length=3), limit: int = Query(10, ge=1, le=50)):
    return query("""SELECT productId, productTitle, SUM(quantity) AS unitsSold,
      SUM(lineTotalMinor) AS salesMinor, SUM(discountMinor) AS discountsMinor
      FROM lakehouse.supersports.order_lines l JOIN lakehouse.supersports.order_sales s USING (aggregateId)
      WHERE l.currency=? AND s.confirmed GROUP BY productId,productTitle ORDER BY salesMinor DESC LIMIT $LIMIT""", currency, limit=limit)


@app.get("/api/reports/refunds")
def refunds(currency: str = Query("INR", min_length=3, max_length=3)):
    return query("""SELECT CAST(occurredAt AS DATE) AS day, reasonCode, COUNT(*) AS events,
      SUM(amountMinor) AS amountMinor FROM lakehouse.supersports.order_refunds
      WHERE currency=? GROUP BY 1,2 ORDER BY 1 DESC LIMIT $LIMIT""", currency, limit=100)
