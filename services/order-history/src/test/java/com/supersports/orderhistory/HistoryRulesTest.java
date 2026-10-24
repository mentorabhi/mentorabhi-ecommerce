package com.supersports.orderhistory;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import java.util.Map;
import org.junit.jupiter.api.Test;

class HistoryRulesTest {
    private static final String ORDER="00000000-0000-4000-8000-000000000002";
    private Map<String,Object> envelope(String type,long sequence){
        Map<String,Object> data=switch(type){
            case "OrderAccepted" -> Map.of("orderId",ORDER,"checkoutRequestId",ORDER,"state","PENDING_PAYMENT","currency","INR","subtotalMinor",100,"discountMinor",0,"taxMinor",0,"shippingMinor",0,"totalMinor",100,"lines",java.util.List.of(Map.of("skuId",ORDER,"productId",ORDER,"productTitle","Test product","quantity",1,"unitPriceMinor",100,"discountMinor",0,"lineTotalMinor",100,"currency","INR")));
            case "OrderConfirmed" -> Map.of("orderId",ORDER,"state","CONFIRMED");
            case "FulfillmentScheduled" -> Map.of("orderId",ORDER,"state","FULFILLMENT_SCHEDULED");
            default -> Map.of("orderId",ORDER,"state","FAILED","reason","QUOTE_EXPIRED");
        };
        return Map.of("eventId","00000000-0000-4000-8000-000000000001","eventType",type,"eventVersion",1,"aggregateType","Order","aggregateId",ORDER,"aggregateSequence",sequence,"occurredAt","2026-10-24T00:00:00Z","customerKey","a".repeat(64),"data",data);
    }
    private Map<String,Object> v2(String type,Map<String,Object> data){return Map.of("eventId","00000000-0000-4000-8000-000000000001","eventType",type,"eventVersion",2,"aggregateType","Order","aggregateId",ORDER,"aggregateSequence",4,"occurredAt","2026-10-24T00:00:00Z","customerKey","a".repeat(64),"data",data);}
    @Test void supportedEventsMapToOrderStatesAndPreserveOwner(){
        assertThat(HistoryRules.parse(envelope("OrderAccepted",1)).state()).isEqualTo("PENDING_PAYMENT");
        assertThat(HistoryRules.parse(envelope("OrderConfirmed",2)).state()).isEqualTo("CONFIRMED");
        assertThat(HistoryRules.parse(envelope("FulfillmentScheduled",3)).state()).isEqualTo("FULFILLMENT_SCHEDULED");
        assertThat(HistoryRules.parse(envelope("OrderCheckoutExpired",4)).customerKey()).isEqualTo("a".repeat(64));
    }
    @Test void rejectsUnknownTypesBadSequenceAndWrongAggregate(){
        assertThatThrownBy(()->HistoryRules.parse(envelope("Unknown",1))).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(()->HistoryRules.parse(envelope("OrderAccepted",0))).isInstanceOf(IllegalArgumentException.class);
        var wrong=new java.util.HashMap<>(envelope("OrderAccepted",1));wrong.put("aggregateType","Cart");
        assertThatThrownBy(()->HistoryRules.parse(wrong)).isInstanceOf(IllegalArgumentException.class);
    }
    @Test void rejectsPrivacyFieldsFractionalSequencesInvalidTimeAndIncompleteSnapshots(){
        for(var change:java.util.List.of(Map.entry("customerSubject",(Object)"private"),Map.entry("customerKey",(Object)"not-hashed"),Map.entry("aggregateSequence",(Object)1.5),Map.entry("occurredAt",(Object)"yesterday"),Map.entry("data",(Object)Map.of()))){
            var invalid=new java.util.HashMap<>(envelope("OrderAccepted",1));invalid.put(change.getKey(),change.getValue());
            assertThatThrownBy(()->HistoryRules.parse(invalid)).isInstanceOf(IllegalArgumentException.class);
        }
        var privateData=new java.util.HashMap<>((Map<String,Object>)envelope("OrderConfirmed",2).get("data"));privateData.put("address","private");
        var invalid=new java.util.HashMap<>(envelope("OrderConfirmed",2));invalid.put("data",privateData);
        assertThatThrownBy(()->HistoryRules.parse(invalid)).isInstanceOf(IllegalArgumentException.class);
    }
    @Test void acceptsV2PostPurchaseFactsAndRejectsUnknownOrPrivateFields(){
        var cancellation=v2("OrderCancelled",Map.of("orderId",ORDER,"state","CANCELLED","operationId","00000000-0000-4000-8000-000000000003","refundMinor",100,"currency","INR","reasonCode","CUSTOMER_REQUEST"));
        assertThat(HistoryRules.parse(cancellation).state()).isEqualTo("CANCELLED");
        var shipment=v2("ShipmentMilestoneRecorded",Map.of("orderId",ORDER,"state","DELIVERED","shipmentState","DELIVERED","shipmentRevision",3,"operationId","00000000-0000-4000-8000-000000000003"));
        assertThat(HistoryRules.parse(shipment).version()).isEqualTo(2);
        var privateData=new java.util.HashMap<>((Map<String,Object>)cancellation.get("data"));privateData.put("reviewText","private");
        assertThatThrownBy(()->HistoryRules.parse(v2("OrderCancelled",privateData))).isInstanceOf(IllegalArgumentException.class);
        var badVersion=new java.util.HashMap<>(cancellation);badVersion.put("eventVersion",1);
        assertThatThrownBy(()->HistoryRules.parse(badVersion)).isInstanceOf(IllegalArgumentException.class);
    }
}
