"""Read-only, allowlisted reporting queries over local Trino."""
import re
from fastapi import FastAPI, HTTPException, Query
from trino.dbapi import connect

app = FastAPI(title="SuperSports analytics reports", version="1.0.0")


def query(sql: str, currency: str, *, days: int = 30, limit: int = 10):
    if not re.fullmatch(r"[A-Z]{3}", currency):
        raise HTTPException(422, "Currency must be a three-letter ISO code")
    if not 7 <= days <= 365 or not 1 <= limit <= 100:
        raise HTTPException(422, "Report range or row limit is outside the supported bounds")
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
def summary(currency: str = Query("INR", min_length=3, max_length=3), days: int = Query(30, ge=7, le=365)):
    row = query("""WITH period_sales AS (
      SELECT * FROM lakehouse.supersports.order_sales
      WHERE currency=? AND occurredAt >= current_timestamp - INTERVAL '$DAYS' DAY
    ), sales AS (
      SELECT COUNT_IF(confirmed) AS confirmed_orders,
             COALESCE(SUM(IF(confirmed,subtotalMinor,0)),0) AS gmv_minor,
             COALESCE(SUM(IF(confirmed,totalMinor,0)),0) AS order_value_minor,
             COALESCE(SUM(IF(confirmed,discountMinor,0)),0) AS discounts_minor
      FROM period_sales
    ), refunds AS (
      SELECT COALESCE(SUM(amountMinor),0) AS refunded_minor,
             COUNT(*) AS refund_events
      FROM lakehouse.supersports.order_refunds
      WHERE currency=? AND occurredAt >= current_timestamp - INTERVAL '$DAYS' DAY
    ), lifecycle AS (
      SELECT COUNT(DISTINCT IF(r.eventType='OrderCancelled',r.aggregateId,NULL)) AS cancellations,
             COUNT(DISTINCT IF(r.eventType='OrderReturnRequested',r.aggregateId,NULL)) AS return_orders
      FROM lakehouse.supersports.raw_lifecycle r
      LEFT JOIN lakehouse.supersports.order_sales s ON s.aggregateId=r.aggregateId
      WHERE r.occurredAt >= current_timestamp - INTERVAL '$DAYS' DAY
        AND ((r.eventType='OrderCancelled' AND json_extract_scalar(r.dataJson,'$.currency')=?)
          OR (r.eventType='OrderReturnRequested' AND s.currency=?))
    ), freshness AS (
      SELECT MAX(occurredAt) AS latest_event_at FROM lakehouse.supersports.raw_lifecycle
    ), units AS (
      SELECT COALESCE(SUM(l.quantity),0) AS units_sold
      FROM lakehouse.supersports.order_lines l JOIN period_sales s USING (aggregateId)
      WHERE s.confirmed
    ) SELECT * FROM sales CROSS JOIN refunds CROSS JOIN lifecycle CROSS JOIN freshness CROSS JOIN units""", currency, days=days)
    return row[0] if row else {}


@app.get("/api/reports/daily-sales")
def daily_sales(currency: str = Query("INR", min_length=3, max_length=3), days: int = Query(30, ge=7, le=365)):
    return query("""SELECT CAST(occurredAt AS DATE) AS day, COUNT(*) AS orders,
      SUM(subtotalMinor) AS \"gmvMinor\", SUM(totalMinor) AS \"orderValueMinor\", SUM(discountMinor) AS \"discountsMinor\"
      FROM lakehouse.supersports.order_sales WHERE currency=? AND confirmed
      AND occurredAt >= current_timestamp - INTERVAL '$DAYS' DAY
      GROUP BY 1 ORDER BY 1 DESC LIMIT $DAYS""", currency, days=days)


@app.get("/api/reports/top-products")
def top_products(currency: str = Query("INR", min_length=3, max_length=3), days: int = Query(30, ge=7, le=365), limit: int = Query(10, ge=1, le=50)):
    return query("""SELECT l.productId, l.productTitle, SUM(l.quantity) AS \"unitsSold\",
      SUM(l.lineTotalMinor) AS \"salesMinor\", SUM(l.discountMinor) AS \"discountsMinor\"
      FROM lakehouse.supersports.order_lines l JOIN lakehouse.supersports.order_sales s USING (aggregateId)
      WHERE l.currency=? AND s.confirmed AND s.occurredAt >= current_timestamp - INTERVAL '$DAYS' DAY
      GROUP BY l.productId,l.productTitle ORDER BY salesMinor DESC LIMIT $LIMIT""", currency, days=days, limit=limit)


@app.get("/api/reports/refunds")
def refunds(currency: str = Query("INR", min_length=3, max_length=3), days: int = Query(30, ge=7, le=365)):
    return query("""SELECT CAST(occurredAt AS DATE) AS day, reasonCode AS \"reasonCode\", COUNT(*) AS events,
      SUM(amountMinor) AS \"amountMinor\" FROM lakehouse.supersports.order_refunds
      WHERE currency=? AND occurredAt >= current_timestamp - INTERVAL '$DAYS' DAY
      GROUP BY 1,2 ORDER BY 1 DESC LIMIT $LIMIT""", currency, days=days, limit=100)
