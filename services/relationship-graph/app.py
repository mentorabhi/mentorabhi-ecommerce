"""Local, bounded product relationship projection API and Kafka consumer."""
import os
import threading
from fastapi import FastAPI, HTTPException, Query
from neo4j import GraphDatabase
from confluent_kafka import Consumer
from order_events import parse_event

app = FastAPI(title="SuperSports relationship graph", version="1.0.0")
driver = GraphDatabase.driver(os.getenv("NEO4J_URI", "bolt://neo4j:7687"),
                              auth=("neo4j", os.environ["GRAPH_DB_PASSWORD"]))


def project_event(event: dict) -> None:
    if event.get("eventType") != "OrderAccepted":
        return
    data = event.get("data") or {}
    products = data.get("lines", [])
    if not isinstance(products, list) or len(products) > 100:
        raise ValueError("Order product list exceeds projection bounds")
    with driver.session() as session:
        session.execute_write(_write_order, event, products)


def _write_order(tx, event, products):
    row = tx.run("MERGE (o:Order {id:$id}) ON CREATE SET o.projected=false SET o.occurredAt=$at RETURN o.projected AS projected",
                 id=event["aggregateId"],at=event["occurredAt"]).single()
    if row["projected"]: return
    for item in products:
        sku = str(item.get("skuId", ""))
        product = str(item.get("productId", ""))
        if not sku or not product:
            continue
        tx.run("MERGE (p:Product {id:$product}) MERGE (s:SKU {id:$sku}) MERGE (p)-[:HAS_SKU]->(s) "
               "WITH s MATCH (o:Order {id:$order}) MERGE (o)-[:CONTAINS]->(s)",
               product=product, sku=sku, order=event["aggregateId"])
    tx.run("""MATCH (o:Order {id:$id})-[:CONTAINS]->(a:SKU), (o)-[:CONTAINS]->(b:SKU)
              WHERE a.id < b.id
              MERGE (a)-[r:BOUGHT_WITH]->(b) SET r.count=coalesce(r.count,0)+1""",
           id=event["aggregateId"])
    tx.run("MATCH (o:Order {id:$id}) SET o.projected=true",id=event["aggregateId"])


def consume() -> None:
    consumer = Consumer({"bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP", "kafka:9092"),
                         "group.id": "supersports-relationship-graph-v1", "auto.offset.reset": "earliest",
                         "enable.auto.commit": False})
    consumer.subscribe([os.getenv("ORDER_EVENT_TOPIC", "commerce.order.events.v1")])
    try:
        while True:
            message = consumer.poll(1.0)
            if message is None:
                continue
            if message.error():
                continue
            try:
                event = parse_event(message.value())
            except ValueError:
                with driver.session() as session:
                    session.run("MERGE (q:QuarantinedRecord {coordinate:$coordinate}) SET q.reason='invalid-lifecycle-contract'",
                                coordinate=f"{message.topic()}:{message.partition()}:{message.offset()}").consume()
            else:
                project_event(event)
            consumer.commit(message=message, asynchronous=False)
    finally:
        consumer.close()


def relationship_query(depth: int) -> str:
    path = "*1" if depth == 1 else "*1..2"
    return f"""MATCH path=(p:Product {{id:$id}})-[:HAS_SKU]->(:SKU)-[:BOUGHT_WITH{path}]-(related:SKU)<-[:HAS_SKU]-(candidate:Product)
               WHERE candidate.id <> p.id
               WITH DISTINCT candidate, min(length(path)) AS distance
               RETURN candidate.id AS productId, distance ORDER BY distance, productId LIMIT $limit"""


@app.on_event("startup")
def start_consumer():
    with driver.session() as session:
        session.run("CREATE CONSTRAINT graph_product_id IF NOT EXISTS FOR (n:Product) REQUIRE n.id IS UNIQUE")
        session.run("CREATE CONSTRAINT graph_sku_id IF NOT EXISTS FOR (n:SKU) REQUIRE n.id IS UNIQUE")
        session.run("CREATE CONSTRAINT graph_order_id IF NOT EXISTS FOR (n:Order) REQUIRE n.id IS UNIQUE")
    threading.Thread(target=consume, daemon=True, name="graph-kafka-projection").start()


@app.get("/health/ready")
def health():
    try:
        driver.verify_connectivity()
        return {"status": "UP"}
    except Exception as exc:
        raise HTTPException(503, "Graph database unavailable") from exc


@app.get("/api/relationships/products/{product_id}")
def related_products(product_id: str, depth: int = Query(1, ge=1, le=2), limit: int = Query(12, ge=1, le=50)):
    query = relationship_query(depth)
    try:
        with driver.session() as session:
            with session.begin_transaction(timeout=1.5) as tx:
                rows = tx.run(query, id=product_id, limit=limit).data()
        return {"productId": product_id, "items": rows}
    except Exception as exc:
        raise HTTPException(503, "Relationship query unavailable") from exc
