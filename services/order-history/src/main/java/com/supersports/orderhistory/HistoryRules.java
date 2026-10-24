package com.supersports.orderhistory;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

/** Consumer-side validation for immutable order lifecycle contract versions 1 and 2. */
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
        if ((version!=1&&version!=2) || !"Order".equals(text(envelope,"aggregateType"))) throw new IllegalArgumentException();
        String type=text(envelope,"eventType"), owner=text(envelope,"customerKey"), occurred=text(envelope,"occurredAt");
        if (!owner.matches("[a-f0-9]{64}")) throw new IllegalArgumentException();
        Instant.parse(occurred);
        var data=object(envelope.get("data"));
        if (!aggregate.equals(uuid(data,"orderId"))) throw new IllegalArgumentException();
        String state;
        if(version==1){
            state=switch(type) {
                case "OrderAccepted" -> "PENDING_PAYMENT";
                case "OrderConfirmed" -> "CONFIRMED";
                case "FulfillmentScheduled" -> "FULFILLMENT_SCHEDULED";
                case "OrderPaymentDeclined","OrderCheckoutExpired" -> "FAILED";
                default -> throw new IllegalArgumentException();
            };
            if(!state.equals(text(data,"state")))throw new IllegalArgumentException();
        }else state=validateV2(type,data);
        if (version==1&&type.equals("OrderAccepted")) {
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
        } else if (version==1&&state.equals("FAILED")) {
            fields(data,"orderId","state","reason");
            if (!Set.of("PAYMENT_DECLINED","QUOTE_EXPIRED").contains(text(data,"reason"))) throw new IllegalArgumentException();
        } else if(version==1)fields(data,"orderId","state");
        return new Event(id,aggregate,type,(int)version,sequence,occurred,owner,state,data);
    }

    private static String validateV2(String type,Map<String,Object> data){
        String state=text(data,"state");
        switch(type){
            case "OrderCancelled" -> {
                fields(data,"orderId","state","operationId","refundMinor","currency","reasonCode");
                uuid(data,"operationId");integer(data,"refundMinor",0);currency(data);
                if(!Set.of("CUSTOMER_REQUEST","SIMULATED_POLICY").contains(text(data,"reasonCode"))||!state.equals("CANCELLED"))throw new IllegalArgumentException();
            }
            case "OrderReturnRequested" -> {
                fields(data,"orderId","state","returnId","lines","policyRevision");uuid(data,"returnId");
                if(!state.equals("DELIVERED"))throw new IllegalArgumentException();integer(data,"policyRevision",1);
                if(!(data.get("lines") instanceof List<?> lines)||lines.isEmpty())throw new IllegalArgumentException();
                for(Object value:lines){var line=object(value);fields(line,"skuId","quantity");uuid(line,"skuId");integer(line,"quantity",1);}
            }
            case "OrderRefundCompleted" -> {
                fields(data,"orderId","state","refundId","amountMinor","currency","reasonCode");uuid(data,"refundId");integer(data,"amountMinor",0);currency(data);
                if(!Set.of("CANCELLED","DELIVERED").contains(state)||!Set.of("CANCELLATION","RETURN").contains(text(data,"reasonCode")))throw new IllegalArgumentException();
            }
            case "ShipmentMilestoneRecorded" -> {
                fields(data,"orderId","state","shipmentState","shipmentRevision","operationId");uuid(data,"operationId");integer(data,"shipmentRevision",1);
                String shipment=text(data,"shipmentState");
                if(!Set.of("HANDED_OFF","IN_TRANSIT","DELIVERED").contains(shipment))throw new IllegalArgumentException();
                String expected=shipment.equals("DELIVERED")?"DELIVERED":"FULFILLMENT_SCHEDULED";
                if(!state.equals(expected))throw new IllegalArgumentException();
            }
            default -> throw new IllegalArgumentException();
        }
        return state;
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
