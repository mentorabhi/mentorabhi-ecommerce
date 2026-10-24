package com.supersports.orderhistory;
import java.util.Map;
import java.util.UUID;
final class HistoryRules {
 private HistoryRules(){}
 static Event parse(Map<String,Object> e){
  UUID id=UUID.fromString(text(e,"eventId")),aggregate=UUID.fromString(text(e,"aggregateId"));
  String type=text(e,"eventType");int version=((Number)e.get("eventVersion")).intValue();long sequence=((Number)e.get("aggregateSequence")).longValue();
  if(version!=1||sequence<1||!"Order".equals(text(e,"aggregateType")))throw new IllegalArgumentException("Unsupported order event envelope");
  var data=(Map<String,Object>)e.get("data");if(data==null)throw new IllegalArgumentException("Order event data is missing");
  var state=switch(type){case "OrderAccepted"->"PENDING_PAYMENT";case "OrderConfirmed"->"CONFIRMED";case "FulfillmentScheduled"->"FULFILLMENT_SCHEDULED";case "OrderPaymentDeclined","OrderCheckoutExpired"->"FAILED";default->throw new IllegalArgumentException("Unsupported order event type");};
  return new Event(id,aggregate,type,version,sequence,text(e,"occurredAt"),text(e,"customerKey"),state,data);
 }
 private static String text(Map<String,Object> m,String key){Object value=m.get(key);if(value==null||value.toString().isBlank())throw new IllegalArgumentException("Missing event field: "+key);return value.toString();}
 record Event(UUID eventId,UUID aggregateId,String eventType,int version,long sequence,String occurredAt,String customerKey,String state,Map<String,Object> data){}
}
