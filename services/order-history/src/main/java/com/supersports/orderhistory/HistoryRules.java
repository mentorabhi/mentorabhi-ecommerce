package com.supersports.orderhistory;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

/** Consumer-side validation of contracts/orders/order-lifecycle-v1.schema.json. */
final class HistoryRules {
    private HistoryRules() {}

    static Event parse(Map<String,Object> envelope) {
        try { return validated(envelope); }
        catch (RuntimeException error) { throw new IllegalArgumentException("INVALID_EVENT_CONTRACT"); }
    }

    private static Event validated(Map<String,Object> envelope) {
        fields(envelope,"eventId","eventType","eventVersion","aggregateType","aggregateId","aggregateSequence","occurredAt","customerKey","data");
        UUID id=uuid(envelope,"eventId"), aggregate=uuid(envelope,"aggregateId");
        long version=integer(envelope,"eventVersion",1), sequence=integer(envelope,"aggregateSequence",1);
        if (version!=1 || !"Order".equals(text(envelope,"aggregateType"))) throw new IllegalArgumentException();
        String type=text(envelope,"eventType"), owner=text(envelope,"customerKey"), occurred=text(envelope,"occurredAt");
        if (!owner.matches("[a-f0-9]{64}")) throw new IllegalArgumentException();
        Instant.parse(occurred);
        String state=switch(type) {
            case "OrderAccepted" -> "PENDING_PAYMENT";
            case "OrderConfirmed" -> "CONFIRMED";
            case "FulfillmentScheduled" -> "FULFILLMENT_SCHEDULED";
            case "OrderPaymentDeclined","OrderCheckoutExpired" -> "FAILED";
            default -> throw new IllegalArgumentException();
        };
        var data=object(envelope.get("data"));
        if (!aggregate.equals(uuid(data,"orderId")) || !state.equals(text(data,"state"))) throw new IllegalArgumentException();
        if (type.equals("OrderAccepted")) {
            fields(data,"orderId","checkoutRequestId","state","currency","subtotalMinor","discountMinor","taxMinor","shippingMinor","totalMinor","lines");
            uuid(data,"checkoutRequestId");currency(data);
            for (String key:List.of("subtotalMinor","discountMinor","taxMinor","shippingMinor","totalMinor")) integer(data,key,0);
            if (!(data.get("lines") instanceof List<?> lines) || lines.isEmpty()) throw new IllegalArgumentException();
            for (Object value:lines) {
                var line=object(value);
                fields(line,"skuId","productId","productTitle","quantity","unitPriceMinor","discountMinor","lineTotalMinor","currency");
                uuid(line,"skuId");uuid(line,"productId");currency(line);
                if (text(line,"productTitle").length()>240) throw new IllegalArgumentException();
                integer(line,"quantity",1);
                for (String key:List.of("unitPriceMinor","discountMinor","lineTotalMinor")) integer(line,key,0);
            }
        } else if (state.equals("FAILED")) {
            fields(data,"orderId","state","reason");
            if (!Set.of("PAYMENT_DECLINED","QUOTE_EXPIRED").contains(text(data,"reason"))) throw new IllegalArgumentException();
        } else fields(data,"orderId","state");
        return new Event(id,aggregate,type,1,sequence,occurred,owner,state,data);
    }

    private static void fields(Map<String,Object> object,String... keys) { if (!object.keySet().equals(Set.of(keys))) throw new IllegalArgumentException(); }
    private static String text(Map<String,Object> object,String key) { if (!(object.get(key) instanceof String value) || value.isBlank()) throw new IllegalArgumentException(); return value; }
    private static UUID uuid(Map<String,Object> object,String key) {
        String value=text(object,key);
        if (!value.matches("(?i)[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}")) throw new IllegalArgumentException();
        return UUID.fromString(value);
    }
    private static long integer(Map<String,Object> object,String key,long minimum) {
        if (!(object.get(key) instanceof Number number)) throw new IllegalArgumentException();
        long value=new java.math.BigDecimal(number.toString()).longValueExact();
        if (value<minimum) throw new IllegalArgumentException();return value;
    }
    private static void currency(Map<String,Object> object) { if (!text(object,"currency").matches("[A-Z]{3}")) throw new IllegalArgumentException(); }
    private static Map<String,Object> object(Object value) { if (!(value instanceof Map<?,?>)) throw new IllegalArgumentException();return (Map<String,Object>)value; }
    record Event(UUID eventId,UUID aggregateId,String eventType,int version,long sequence,String occurredAt,String customerKey,String state,Map<String,Object> data) {}
}
