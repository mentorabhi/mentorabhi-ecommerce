package com.supersports.orders;

import java.sql.Timestamp;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

@Repository
class OrdersRepository {
    private final JdbcTemplate jdbc;
    OrdersRepository(JdbcTemplate jdbc) { this.jdbc = jdbc; }

    @Transactional
    Map<String,Object> claimSaga() {
        var rows=jdbc.queryForList("SELECT order_id,current_step,fence FROM checkout_saga WHERE state IN ('RUNNING','FULFILLMENT_PENDING') AND next_attempt_at<=now() AND (lease_until IS NULL OR lease_until<now()) ORDER BY next_attempt_at LIMIT 1 FOR UPDATE SKIP LOCKED");
        if(rows.isEmpty())return null;
        var row=rows.getFirst();UUID id=(UUID)row.get("order_id");long fence=((Number)row.get("fence")).longValue()+1;
        jdbc.update("UPDATE checkout_saga SET lease_owner=?,lease_until=now()+interval '30 seconds',fence=?,attempt=attempt+1,updated_at=now() WHERE order_id=?",UUID.randomUUID().toString(),fence,id);
        var result=new java.util.HashMap<String,Object>(row);result.put("orderId",id);result.put("fence",fence);return result;
    }
    @Transactional
    void sagaStep(UUID id,long fence,String expected,String next,String step,Map<String,Object> result) {
        int changed=jdbc.update("UPDATE checkout_saga SET current_step=?,state=?,lease_owner=NULL,lease_until=NULL,next_attempt_at=now(),last_error_code=NULL,updated_at=now() WHERE order_id=? AND fence=? AND current_step=?",next,next.equals("DONE")?"CONFIRMED":next.equals("FULFILLMENT")?"FULFILLMENT_PENDING":"RUNNING",id,fence,expected);
        if(changed!=1)return;
        jdbc.update("INSERT INTO checkout_saga_step(order_id,step,operation_key,state,result) VALUES (?,?,?,'SUCCEEDED',?::jsonb) ON CONFLICT(order_id,step) DO UPDATE SET state='SUCCEEDED',result=EXCLUDED.result,error_code=NULL,updated_at=now()",id,step,id+":"+step.toLowerCase(java.util.Locale.ROOT),OrdersJson.write(result));
        if(next.equals("DONE")){jdbc.update("UPDATE customer_order SET state='CONFIRMED',updated_at=now() WHERE id=?",id);jdbc.update("UPDATE checkout_saga SET state='FULFILLMENT_PENDING',current_step='SCHEDULE_FULFILLMENT' WHERE order_id=?",id);jdbc.update("INSERT INTO order_outbox(aggregate_id,event_type,payload) VALUES (?,'OrderConfirmed',?::jsonb)",id,OrdersJson.write(Map.of("orderId",id,"state","CONFIRMED")));}
        if(next.equals("FULFILLMENT_DONE")){jdbc.update("UPDATE customer_order SET state='FULFILLMENT_SCHEDULED',updated_at=now() WHERE id=?",id);jdbc.update("UPDATE checkout_saga SET state='COMPLETED',current_step='COMPLETED' WHERE order_id=?",id);jdbc.update("INSERT INTO order_outbox(aggregate_id,event_type,payload) VALUES (?,'FulfillmentScheduled',?::jsonb)",id,OrdersJson.write(Map.of("orderId",id,"state","FULFILLMENT_SCHEDULED")));}
    }
    @Transactional void sagaRetry(UUID id,long fence,String code){jdbc.update("UPDATE checkout_saga SET lease_owner=NULL,lease_until=NULL,next_attempt_at=now()+least(interval '30 seconds', interval '1 second' * power(2,least(attempt,5))),last_error_code=?,updated_at=now() WHERE order_id=? AND fence=?",code,id,fence);}
    @Transactional void failDeclined(UUID id,long fence){int changed=jdbc.update("UPDATE checkout_saga SET state='FAILED',current_step='FAILED',lease_owner=NULL,lease_until=NULL,last_error_code='PAYMENT_DECLINED',updated_at=now() WHERE order_id=? AND fence=? AND current_step='AUTHORIZE'",id,fence);if(changed==1){jdbc.update("UPDATE customer_order SET state='FAILED',updated_at=now() WHERE id=?",id);jdbc.update("INSERT INTO checkout_saga_step(order_id,step,operation_key,state,error_code) VALUES (?,'PAYMENT_DECLINED',?,'FAILED','PAYMENT_DECLINED') ON CONFLICT(order_id,step) DO UPDATE SET state='FAILED',error_code='PAYMENT_DECLINED',updated_at=now()",id,id+":payment-declined");jdbc.update("INSERT INTO order_outbox(aggregate_id,event_type,payload) VALUES (?,'OrderPaymentDeclined',?::jsonb)",id,OrdersJson.write(Map.of("orderId",id,"state","FAILED","reason","PAYMENT_DECLINED")));}}
    @Transactional void failExpiredQuote(UUID id,long fence){int changed=jdbc.update("UPDATE checkout_saga SET state='FAILED',current_step='FAILED',lease_owner=NULL,lease_until=NULL,last_error_code='QUOTE_EXPIRED',updated_at=now() WHERE order_id=? AND fence=? AND current_step='RESERVE_INVENTORY'",id,fence);if(changed==1){jdbc.update("UPDATE customer_order SET state='FAILED',updated_at=now() WHERE id=?",id);jdbc.update("INSERT INTO checkout_saga_step(order_id,step,operation_key,state,error_code) VALUES (?,'QUOTE_EXPIRED',?,'FAILED','QUOTE_EXPIRED') ON CONFLICT(order_id,step) DO UPDATE SET state='FAILED',error_code='QUOTE_EXPIRED',updated_at=now()",id,id+":quote-expired");jdbc.update("INSERT INTO order_outbox(aggregate_id,event_type,payload) VALUES (?,'OrderCheckoutExpired',?::jsonb)",id,OrdersJson.write(Map.of("orderId",id,"state","FAILED","reason","QUOTE_EXPIRED")));}}
    @Transactional Map<String,Object> sagaOrder(UUID id){var rows=jdbc.queryForList("SELECT o.total_minor AS \"totalMinor\",o.currency,o.customer_subject AS \"customerSubject\",o.quote_snapshot AS \"quoteSnapshot\",o.configuration_revision AS \"configurationRevision\",s.current_step AS \"currentStep\" FROM customer_order o JOIN checkout_saga s ON s.order_id=o.id WHERE o.id=?",id);if(rows.isEmpty())return null;var result=new java.util.HashMap<>(rows.getFirst());result.put("quoteSnapshot",OrdersJson.readMap(result.get("quoteSnapshot")));result.put("lines",jdbc.queryForList("SELECT sku_id AS \"skuId\",quantity FROM customer_order_line WHERE order_id=?",id));return result;}
    @Transactional void repairMissingSimulationSettings(UUID id,long fence,Map<String,Object> settings){jdbc.update("UPDATE customer_order o SET quote_snapshot=jsonb_set(o.quote_snapshot,'{simulationSettings}',?::jsonb,true),configuration_revision=? FROM checkout_saga s WHERE o.id=? AND s.order_id=o.id AND s.fence=? AND s.current_step='RESERVE_INVENTORY' AND o.quote_snapshot->'simulationSettings' IS NULL",OrdersJson.write(settings),((Number)settings.get("revision")).longValue(),id,fence);}

    @Transactional
    Map<String,Object> claim(String subject,String key,String payloadHash,Map<UUID,Integer> lines,String coupon) {
        UUID id=UUID.randomUUID(); Instant lease=Instant.now().plusSeconds(120);
        jdbc.update("INSERT INTO checkout_request(id,customer_subject,idempotency_key,payload_hash,status,validation_lease_until,payload) VALUES (?,?,?,?,'VALIDATING',?,?::jsonb) ON CONFLICT(customer_subject,idempotency_key) DO NOTHING",id,subject,key,payloadHash,Timestamp.from(lease),OrdersJson.write(Map.of("lines",lines.entrySet().stream().map(e->Map.of("skuId",e.getKey().toString(),"quantity",e.getValue())).toList(),"couponCode",coupon==null?"":coupon.trim().toUpperCase(java.util.Locale.ROOT))));
        var rows=jdbc.queryForList("SELECT id,payload_hash,status,validation_lease_until,order_id,error_code FROM checkout_request WHERE customer_subject=? AND idempotency_key=? FOR UPDATE",subject,key);
        var row=rows.getFirst();
        if(!payloadHash.equals(row.get("payload_hash")))return Map.of("conflict",true);
        boolean resume="VALIDATING".equals(row.get("status")) && ((Timestamp)row.get("validation_lease_until")).toInstant().isBefore(Instant.now());
        if(resume)jdbc.update("UPDATE checkout_request SET validation_lease_until=?,updated_at=now() WHERE id=?",Timestamp.from(lease),row.get("id"));
        var result=new java.util.HashMap<String,Object>();result.put("requestId",row.get("id"));result.put("status",row.get("status"));result.put("replayed",!id.equals(row.get("id")));result.put("resumeValidation",resume);
        if(row.get("order_id")!=null)result.put("orderId",row.get("order_id"));if(row.get("error_code")!=null)result.put("errorCode",row.get("error_code"));return result;
    }
    @Transactional
    Map<String,Object> accept(UUID requestId,String subject,UUID orderId,Map<String,Object> address,Map<String,Object> quote,Map<String,Object> settings,long configRevision,long tax,long shipping,long total) {
        var claims=jdbc.queryForList("SELECT status,customer_subject FROM checkout_request WHERE id=? FOR UPDATE",requestId);
        if(claims.isEmpty()||!subject.equals(claims.getFirst().get("customer_subject")))throw new IllegalStateException("Checkout claim ownership changed");
        if("ACCEPTED".equals(claims.getFirst().get("status")))return Map.of("requestId",requestId,"status","ACCEPTED");
        Map<String,Object> snapshot=new java.util.LinkedHashMap<>((Map<String,Object>)quote.get("snapshot"));snapshot.put("simulationSettings",settings);
        String currency=snapshot.get("currency").toString();long subtotal=((Number)snapshot.get("subtotalMinor")).longValue(),discount=((Number)snapshot.get("discountMinor")).longValue();
        jdbc.update("INSERT INTO customer_order(id,checkout_request_id,customer_subject,state,currency,subtotal_minor,discount_minor,tax_minor,shipping_minor,total_minor,address_snapshot,quote_snapshot,configuration_revision) VALUES (?, ?, ?, 'PENDING_PAYMENT', ?, ?, ?, ?, ?, ?, ?::jsonb, ?::jsonb, ?)",orderId,requestId,subject,currency,subtotal,discount,tax,shipping,total,OrdersJson.write(address),OrdersJson.write(snapshot),configRevision);
        for(Object raw:(List<?>)snapshot.get("lines")){Map<String,Object> line=(Map<String,Object>)raw;jdbc.update("INSERT INTO customer_order_line(order_id,sku_id,product_id,product_title,quantity,unit_price_minor,discount_minor,line_total_minor,currency) VALUES (?,?,?,?,?,?,?,?,?)",orderId,UUID.fromString(line.get("skuId").toString()),UUID.fromString(line.get("productId").toString()),line.get("productTitle"),line.get("quantity"),line.get("unitPriceMinor"),line.get("discountMinor"),line.get("lineTotalMinor"),line.get("currency"));}
        jdbc.update("INSERT INTO checkout_saga(order_id,state,current_step) VALUES (?,'RUNNING','RESERVE_INVENTORY')",orderId);
        jdbc.update("INSERT INTO checkout_saga_step(order_id,step,operation_key,state) VALUES (?,'RESERVE_INVENTORY',?,'PENDING')",orderId,orderId+":reserve-inventory");
        jdbc.update("INSERT INTO order_outbox(aggregate_id,event_type,payload) VALUES (?,'OrderAccepted',?::jsonb)",orderId,OrdersJson.write(Map.of("orderId",orderId,"checkoutRequestId",requestId,"state","PENDING_PAYMENT")));
        jdbc.update("UPDATE checkout_request SET status='ACCEPTED',order_id=?,error_code=NULL,updated_at=now() WHERE id=?",orderId,requestId);
        return Map.of("requestId",requestId,"orderId",orderId,"status","ACCEPTED","state","PENDING_PAYMENT","currency",currency,"subtotalMinor",subtotal,"discountMinor",discount,"taxMinor",tax,"shippingMinor",shipping,"totalMinor",total);
    }
    @Transactional void reject(UUID requestId,String code){jdbc.update("UPDATE checkout_request SET status='REJECTED',error_code=?,updated_at=now() WHERE id=? AND status='VALIDATING'",code,requestId);}
    Map<String,Object> request(UUID id,String subject) {
        List<Map<String,Object>> rows=jdbc.queryForList("SELECT id,status,order_id,error_code,created_at,updated_at FROM checkout_request WHERE id=? AND customer_subject=?",id,subject);
        return rows.isEmpty()?null:rows.getFirst();
    }
    List<Map<String,Object>> orders(String subject) {
        return jdbc.queryForList("SELECT id,state,currency,subtotal_minor AS \"subtotalMinor\",discount_minor AS \"discountMinor\",tax_minor AS \"taxMinor\",shipping_minor AS \"shippingMinor\",total_minor AS \"totalMinor\",created_at AS \"createdAt\" FROM customer_order WHERE customer_subject=? ORDER BY created_at DESC LIMIT 100",subject);
    }
    Map<String,Object> order(UUID id,String subject) {
        var rows=jdbc.queryForList("SELECT id,state,currency,subtotal_minor AS \"subtotalMinor\",discount_minor AS \"discountMinor\",tax_minor AS \"taxMinor\",shipping_minor AS \"shippingMinor\",total_minor AS \"totalMinor\",address_snapshot AS \"addressSnapshot\",quote_snapshot AS \"quoteSnapshot\",created_at AS \"createdAt\" FROM customer_order WHERE id=? AND customer_subject=?",id,subject);
        if(rows.isEmpty())return null;var result=new java.util.HashMap<>(rows.getFirst());result.put("addressSnapshot",OrdersJson.readMap(result.get("addressSnapshot")));result.put("quoteSnapshot",OrdersJson.readMap(result.get("quoteSnapshot")));result.put("lines",jdbc.queryForList("SELECT sku_id AS \"skuId\",product_id AS \"productId\",product_title AS \"productTitle\",quantity,unit_price_minor AS \"unitPriceMinor\",discount_minor AS \"discountMinor\",line_total_minor AS \"lineTotalMinor\",currency FROM customer_order_line WHERE order_id=? ORDER BY sku_id",id));return result;
    }
}
