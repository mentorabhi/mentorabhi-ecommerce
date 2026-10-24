package com.supersports.orders;

import java.sql.Timestamp;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;
import org.springframework.transaction.support.TransactionTemplate;

@Component
class OutboxBackfill implements ApplicationRunner {
    private final JdbcTemplate jdbc;
    private final OutboxEventWriter events;
    private final TransactionTemplate transaction;

    OutboxBackfill(JdbcTemplate jdbc,OutboxEventWriter events,TransactionTemplate transaction) {this.jdbc=jdbc;this.events=events;this.transaction=transaction;}

    @Override public void run(ApplicationArguments args) {
        transaction.executeWithoutResult(status -> {
            var rows=jdbc.queryForList("SELECT o.id,o.aggregate_id,o.aggregate_sequence,o.event_type,o.payload::text AS payload,o.created_at,c.customer_subject FROM order_outbox o LEFT JOIN customer_order c ON c.id=o.aggregate_id WHERE o.event_id IS NULL ORDER BY o.id FOR UPDATE OF o");
            for(var row:rows){
                Object subject=row.get("customer_subject");if(subject==null)throw new IllegalStateException("Legacy outbox row has no matching customer order; CDC startup is blocked for repair");
                long id=((Number)row.get("id")).longValue();UUID orderId=(UUID)row.get("aggregate_id");
                Map<String,Object> data=OrdersJson.readMap(row.get("payload"));
                String eventType=row.get("event_type").toString();String key=events.customerKey(subject.toString());
                var envelope=new LinkedHashMap<String,Object>();envelope.put("eventId",OutboxEventWriter.legacyEventId(id));envelope.put("eventType",eventType);envelope.put("eventVersion",1);envelope.put("aggregateType","Order");envelope.put("aggregateId",orderId);envelope.put("aggregateSequence",((Number)row.get("aggregate_sequence")).longValue());envelope.put("occurredAt",((Timestamp)row.get("created_at")).toInstant().toString());envelope.put("customerKey",key);envelope.put("data",data);
                if("OrderAccepted".equals(eventType)){
                    var header=jdbc.queryForMap("SELECT currency,subtotal_minor AS \"subtotalMinor\",discount_minor AS \"discountMinor\",tax_minor AS \"taxMinor\",shipping_minor AS \"shippingMinor\",total_minor AS \"totalMinor\" FROM customer_order WHERE id=?",orderId);
                    data.putAll(header);data.put("lines",jdbc.queryForList("SELECT sku_id AS \"skuId\",product_id AS \"productId\",product_title AS \"productTitle\",quantity,unit_price_minor AS \"unitPriceMinor\",discount_minor AS \"discountMinor\",line_total_minor AS \"lineTotalMinor\",currency FROM customer_order_line WHERE order_id=? ORDER BY sku_id",orderId));envelope.put("data",data);
                }
                jdbc.update("UPDATE order_outbox SET event_id=?,customer_key=?,aggregate_type='Order',event_version=1,payload=?::jsonb WHERE id=?",envelope.get("eventId"),key,OrdersJson.write(envelope),id);
            }
            jdbc.update("ALTER TABLE order_outbox ALTER COLUMN event_id SET NOT NULL, ALTER COLUMN event_version SET NOT NULL, ALTER COLUMN aggregate_sequence SET NOT NULL, ALTER COLUMN customer_key SET NOT NULL, ALTER COLUMN aggregate_type SET NOT NULL");
        });
        events.enableAfterBackfill();
    }
}
