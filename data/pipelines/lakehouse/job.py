"""Replayable Spark ingestion for allowlisted Debezium lifecycle events."""
from __future__ import annotations

from pyspark.sql import SparkSession, functions as F, types as T
from order_events import valid_event

DATA_SCHEMA = T.StructType([
    T.StructField("orderId", T.StringType()), T.StructField("currency", T.StringType()),
    T.StructField("subtotalMinor", T.LongType()), T.StructField("discountMinor", T.LongType()),
    T.StructField("taxMinor", T.LongType()), T.StructField("shippingMinor", T.LongType()),
    T.StructField("totalMinor", T.LongType()), T.StructField("amountMinor", T.LongType()),
    T.StructField("state", T.StringType()),
    T.StructField("reasonCode", T.StringType()),
    T.StructField("lines", T.ArrayType(T.StructType([
        T.StructField("skuId", T.StringType()), T.StructField("productId", T.StringType()),
        T.StructField("productTitle", T.StringType()), T.StructField("quantity", T.LongType()),
        T.StructField("lineTotalMinor", T.LongType()), T.StructField("discountMinor", T.LongType()),
    ]))),
])
EVENT_SCHEMA = T.StructType([
    T.StructField("eventId", T.StringType()), T.StructField("eventType", T.StringType()),
    T.StructField("eventVersion", T.IntegerType()), T.StructField("aggregateType", T.StringType()),
    T.StructField("aggregateId", T.StringType()), T.StructField("aggregateSequence", T.LongType()),
    T.StructField("occurredAt", T.TimestampType()), T.StructField("data", DATA_SCHEMA),
])
CDC_SCHEMA = T.StructType([T.StructField("after", T.StructType([T.StructField("payload", T.StringType())]))])


def build_session() -> SparkSession:
    import os
    return (SparkSession.builder.appName("supersports-lifecycle-lakehouse")
            .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
            .config("spark.sql.catalog.local", "org.apache.iceberg.spark.SparkCatalog")
            .config("spark.sql.catalog.local.type", "jdbc")
            .config("spark.sql.catalog.local.uri", "jdbc:postgresql://postgres:5432/lakehouse")
            .config("spark.sql.catalog.local.jdbc.user", "supersports_lakehouse")
            .config("spark.sql.catalog.local.jdbc.password", os.environ["LAKEHOUSE_DB_PASSWORD"])
            .config("spark.sql.catalog.local.warehouse", "file:///warehouse")
            .config("spark.sql.catalog.local.io-impl", "org.apache.iceberg.hadoop.HadoopFileIO")
            .getOrCreate())


def ingest(spark: SparkSession, bootstrap: str, topic: str, starting_offsets: str) -> None:
    source = (spark.read.format("kafka").option("kafka.bootstrap.servers", bootstrap)
              .option("subscribe", topic).option("startingOffsets", starting_offsets)
              .option("endingOffsets", "latest").load())
    parsed = (source.selectExpr("CAST(value AS STRING) AS raw", "topic", "partition", "offset", "timestamp AS kafka_timestamp")
              .withColumn("validContract", F.udf(valid_event,T.BooleanType())("raw"))
              .withColumn("event", F.from_json("raw", EVENT_SCHEMA)))
    valid = parsed.filter(F.col("validContract")).select(
        F.col("topic").alias("sourceTopic"), F.col("partition").alias("sourcePartition"),
        F.col("offset").alias("sourceOffset"), F.col("kafka_timestamp").alias("kafkaTimestamp"), "event.eventId", "event.eventType",
        "event.eventVersion", "event.aggregateType", "event.aggregateId", "event.aggregateSequence",
        "event.occurredAt", F.to_json("event.data").alias("dataJson")).dropDuplicates(["eventId"])
    invalid = parsed.filter(~F.col("validContract")).select(
        F.col("topic").alias("sourceTopic"), F.col("partition").alias("sourcePartition"),
        F.col("offset").alias("sourceOffset"), F.col("kafka_timestamp").alias("kafkaTimestamp")) \
        .withColumn("quarantineReason", F.lit("invalid-or-tombstone-envelope"))
    spark.sql("CREATE NAMESPACE IF NOT EXISTS local.supersports")
    valid.createOrReplaceTempView("incoming_events")
    spark.sql("""CREATE TABLE IF NOT EXISTS local.supersports.raw_lifecycle (
      eventId STRING, eventType STRING, eventVersion INT, aggregateType STRING, aggregateId STRING,
      aggregateSequence BIGINT, occurredAt TIMESTAMP, dataJson STRING,
      sourceTopic STRING, sourcePartition INT, sourceOffset BIGINT, kafkaTimestamp TIMESTAMP, ingestedAt TIMESTAMP
    ) USING iceberg TBLPROPERTIES ('format-version'='2')""")
    spark.sql("""MERGE INTO local.supersports.raw_lifecycle t USING (
      SELECT eventId,eventType,eventVersion,aggregateType,aggregateId,aggregateSequence,occurredAt,dataJson,
      sourceTopic,sourcePartition,sourceOffset,kafkaTimestamp,current_timestamp() AS ingestedAt FROM incoming_events
    ) s ON t.eventId=s.eventId
    WHEN NOT MATCHED THEN INSERT *""")
    # Quarantine is a replayable projection of the current contract result,
    # not a permanent record of historical parser decisions. Rebuild it so
    # repaired validators cannot leave formerly rejected valid coordinates.
    spark.sql("DROP TABLE IF EXISTS local.supersports.quarantined_records")
    spark.sql("""CREATE TABLE local.supersports.quarantined_records (
      sourceTopic STRING, sourcePartition INT, sourceOffset BIGINT, kafkaTimestamp TIMESTAMP, quarantineReason STRING
    ) USING iceberg""")
    invalid.createOrReplaceTempView("incoming_quarantine")
    spark.sql("INSERT INTO local.supersports.quarantined_records SELECT * FROM incoming_quarantine")
    raw = spark.table("local.supersports.raw_lifecycle")
    confirmed_ids = raw.filter(F.col("eventType") == "OrderConfirmed").select("aggregateId").distinct()
    confirmed_ids.createOrReplaceTempView("confirmed_orders")
    raw.filter(F.col("eventType") == "OrderAccepted").select(
        "eventId", "aggregateId", "occurredAt", F.get_json_object("dataJson", "$.currency").alias("currency"),
        F.get_json_object("dataJson", "$.subtotalMinor").cast("long").alias("subtotalMinor"),
        F.get_json_object("dataJson", "$.discountMinor").cast("long").alias("discountMinor"),
        F.get_json_object("dataJson", "$.taxMinor").cast("long").alias("taxMinor"),
        F.get_json_object("dataJson", "$.shippingMinor").cast("long").alias("shippingMinor"),
        F.get_json_object("dataJson", "$.totalMinor").cast("long").alias("totalMinor")) \
        .createOrReplaceTempView("order_sales_source")
    raw.filter(F.col("eventType") == "OrderRefundCompleted").select(
        "eventId", "aggregateId", "occurredAt", F.get_json_object("dataJson", "$.currency").alias("currency"),
        F.get_json_object("dataJson", "$.amountMinor").cast("long").alias("amountMinor"),
        F.get_json_object("dataJson", "$.reasonCode").alias("reasonCode")) \
        .createOrReplaceTempView("order_refunds_source")
    spark.sql("""CREATE OR REPLACE TABLE local.supersports.order_sales USING iceberg AS
      SELECT s.*, c.aggregateId IS NOT NULL AS confirmed
      FROM order_sales_source s LEFT JOIN confirmed_orders c ON s.aggregateId=c.aggregateId""")
    spark.sql("CREATE OR REPLACE TABLE local.supersports.order_refunds USING iceberg AS SELECT * FROM order_refunds_source")
    raw.filter(F.col("eventType") == "OrderAccepted").select(
        "aggregateId", F.get_json_object("dataJson", "$.currency").alias("currency"),
        F.explode_outer(F.from_json(F.get_json_object("dataJson", "$.lines"), T.ArrayType(DATA_SCHEMA["lines"].dataType.elementType))).alias("line")) \
        .select("aggregateId", "currency", F.col("line.skuId").alias("skuId"),
                F.col("line.productId").alias("productId"), F.col("line.productTitle").alias("productTitle"),
                F.col("line.quantity").alias("quantity"), F.col("line.lineTotalMinor").alias("lineTotalMinor"),
                F.col("line.discountMinor").alias("discountMinor")) \
        .createOrReplaceTempView("order_lines_source")
    spark.sql("CREATE OR REPLACE TABLE local.supersports.order_lines USING iceberg AS SELECT * FROM order_lines_source")


if __name__ == "__main__":
    import os
    session = build_session()
    try:
        ingest(session, os.getenv("KAFKA_BOOTSTRAP", "kafka:9092"),
               os.getenv("ORDER_EVENT_TOPIC", "commerce.order.events.v1"),
               os.getenv("STARTING_OFFSETS", "earliest"))
    finally:
        session.stop()
