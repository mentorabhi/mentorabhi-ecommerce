package com.supersports.orders;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

@Repository
class SyntheticOrderRepository {
    private final JdbcTemplate jdbc;
    private final OutboxEventWriter events;
    SyntheticOrderRepository(JdbcTemplate jdbc, OutboxEventWriter events) { this.jdbc = jdbc; this.events = events; }

    @Transactional
    List<Map<String,Object>> importBatch(List<SyntheticOrderImportController.OrderFixture> orders) {
        var result = new ArrayList<Map<String,Object>>(orders.size());
        for (var order : orders) result.add(importOne(order));
        return result;
    }

    private Map<String,Object> importOne(SyntheticOrderImportController.OrderFixture order) {
        String hash = hash(OrdersJson.write(order));
        jdbc.queryForList("SELECT pg_advisory_xact_lock(hashtextextended(?,0))", order.sourceRef());
        var existing = jdbc.queryForList("SELECT order_id,payload_hash FROM synthetic_order_source WHERE source_ref=?", order.sourceRef());
        if (!existing.isEmpty()) {
            var row = existing.getFirst();
            if (!hash.equals(row.get("payload_hash").toString().trim())) throw new IllegalStateException("Synthetic source reference conflicts with existing order data");
            return Map.of("sourceRef", order.sourceRef(), "orderId", row.get("order_id"), "replayed", true);
        }
        UUID requestId = UUID.randomUUID();
        UUID orderId = UUID.randomUUID();
        Instant at = order.occurredAt();
        jdbc.update("INSERT INTO checkout_request(id,customer_subject,idempotency_key,payload_hash,status,validation_lease_until,order_id,created_at,updated_at) VALUES (?,?,?,?,'ACCEPTED',?,?,?,?)",
                requestId, order.customerSubject(), order.sourceRef(), hash, Timestamp.from(at), orderId, Timestamp.from(at), Timestamp.from(at));
        jdbc.update("INSERT INTO customer_order(id,checkout_request_id,customer_subject,state,currency,subtotal_minor,discount_minor,tax_minor,shipping_minor,total_minor,address_snapshot,quote_snapshot,configuration_revision,created_at,updated_at) VALUES (?,?,?,'CONFIRMED',?,?,?,?,?,?,?::jsonb,?::jsonb,?,?,?)",
                orderId, requestId, order.customerSubject(), order.currency(), order.subtotalMinor(), order.discountMinor(), order.taxMinor(),
                order.shippingMinor(), order.totalMinor(), OrdersJson.write(order.addressSnapshot()), OrdersJson.write(Map.of("sourceRef", order.sourceRef(), "synthetic", true)), 1L, Timestamp.from(at), Timestamp.from(at));
        var eventLines = new ArrayList<Map<String,Object>>(order.lines().size());
        for (var line : order.lines()) {
            UUID sku = UUID.fromString(line.skuId());
            jdbc.update("INSERT INTO customer_order_line(order_id,sku_id,product_id,product_title,quantity,unit_price_minor,discount_minor,line_total_minor,currency) VALUES (?,?,?,?,?,?,?,?,?)",
                    orderId, sku, UUID.fromString(line.productId()), line.productTitle(), line.quantity(), line.unitPriceMinor(), line.discountMinor(), line.lineTotalMinor(), line.currency());
            eventLines.add(Map.of("skuId", sku, "productId", UUID.fromString(line.productId()), "productTitle", line.productTitle(),
                    "quantity", line.quantity(), "unitPriceMinor", line.unitPriceMinor(), "discountMinor", line.discountMinor(),
                    "lineTotalMinor", line.lineTotalMinor(), "currency", line.currency()));
        }
        jdbc.update("INSERT INTO checkout_saga(order_id,state,current_step,updated_at) VALUES (?,'COMPLETED','COMPLETED',?)", orderId, Timestamp.from(at));
        jdbc.update("INSERT INTO synthetic_order_source(source_ref,order_id,payload_hash,created_at) VALUES (?,?,?,now())", order.sourceRef(), orderId, hash);
        events.appendSynthetic(orderId, order.customerSubject(), "OrderAccepted", Map.of(
                "orderId", orderId, "checkoutRequestId", requestId, "state", "PENDING_PAYMENT", "currency", order.currency(),
                "subtotalMinor", order.subtotalMinor(), "discountMinor", order.discountMinor(), "taxMinor", order.taxMinor(),
                "shippingMinor", order.shippingMinor(), "totalMinor", order.totalMinor(), "lines", eventLines), at);
        events.appendSynthetic(orderId, order.customerSubject(), "OrderConfirmed", Map.of("orderId", orderId, "state", "CONFIRMED"), at.plusSeconds(60));
        return Map.of("sourceRef", order.sourceRef(), "orderId", orderId, "replayed", false);
    }

    private static String hash(String value) {
        try { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8))); }
        catch (java.security.NoSuchAlgorithmException impossible) { throw new IllegalStateException("SHA-256 is unavailable", impossible); }
    }
}
