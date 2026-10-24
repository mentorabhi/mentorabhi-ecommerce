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
    private final OutboxEventWriter eventWriter;
    OrdersRepository(JdbcTemplate jdbc,OutboxEventWriter eventWriter) { this.jdbc = jdbc;this.eventWriter=eventWriter; }

    @Transactional Map<String,Object> startCancellation(UUID orderId,String subject,String key,String payloadHash,long shipmentRevision){
        var owned=jdbc.queryForList("SELECT o.state,o.currency,o.total_minor,s.fence FROM customer_order o JOIN checkout_saga s ON s.order_id=o.id WHERE o.id=? AND o.customer_subject=? FOR UPDATE OF o,s",orderId,subject);
        if(owned.isEmpty())return null;var order=owned.getFirst();
        var sameKey=jdbc.queryForList("SELECT operation_id,order_id,payload_hash,status,current_step,fence FROM post_purchase_operation WHERE customer_subject=? AND idempotency_key=? FOR UPDATE",subject,key);
        if(!sameKey.isEmpty()){var prior=sameKey.getFirst();if(!orderId.equals(prior.get("order_id"))||!payloadHash.equals(prior.get("payload_hash")))throw new IllegalStateException("IDEMPOTENCY_CONFLICT");return new java.util.HashMap<>(prior);}
        if(!"FULFILLMENT_SCHEDULED".equals(order.get("state")))throw new IllegalStateException("ORDER_NOT_CANCELLABLE");
        UUID id=UUID.randomUUID();long fence=((Number)order.get("fence")).longValue()+1;
        int inserted=jdbc.update("INSERT INTO post_purchase_operation(operation_id,order_id,customer_subject,idempotency_key,payload_hash,operation_type,status,current_step,fence,expected_shipment_revision) VALUES (?,?,?, ?,?,'CANCEL','PENDING','CLAIM_SHIPMENT',?,?) ON CONFLICT DO NOTHING",id,orderId,subject,key,payloadHash,fence,shipmentRevision);
        if(inserted==0){var prior=jdbc.queryForList("SELECT operation_id,order_id,payload_hash,status,current_step,fence FROM post_purchase_operation WHERE customer_subject=? AND idempotency_key=? OR order_id=? AND operation_type='CANCEL' FOR UPDATE",subject,key,orderId);
            if(prior.isEmpty())throw new IllegalStateException("CANCELLATION_CONFLICT");var row=prior.getFirst();
            if(!orderId.equals(row.get("order_id"))||!payloadHash.equals(row.get("payload_hash")))throw new IllegalStateException("IDEMPOTENCY_CONFLICT");
            return new java.util.HashMap<>(row);
        }
        return Map.of("operation_id",id,"order_id",orderId,"status","PENDING","current_step","CLAIM_SHIPMENT","fence",fence,"currency",order.get("currency"),"total_minor",order.get("total_minor"),"expected_shipment_revision",shipmentRevision,"replayed",false);
    }

    @Transactional Map<String,Object> claimPostPurchase(){
        var rows=jdbc.queryForList("SELECT operation_id,order_id,current_step,fence,expected_shipment_revision FROM post_purchase_operation WHERE status IN ('PENDING','RUNNING') AND next_attempt_at<=now() AND (lease_until IS NULL OR lease_until<now()) ORDER BY next_attempt_at LIMIT 1 FOR UPDATE SKIP LOCKED");
        if(rows.isEmpty())return null;var row=rows.getFirst();UUID operation=(UUID)row.get("operation_id");long fence=((Number)row.get("fence")).longValue()+1;
        jdbc.update("UPDATE post_purchase_operation SET status='RUNNING',lease_owner=?,lease_until=now()+interval '30 seconds',fence=?,attempt=attempt+1,updated_at=now() WHERE operation_id=?",UUID.randomUUID().toString(),fence,operation);
        var result=new java.util.HashMap<String,Object>(row);result.put("fence",fence);
        var details=jdbc.queryForList("SELECT customer_subject,currency,total_minor FROM customer_order WHERE id=?",row.get("order_id")).getFirst();result.putAll(details);
        return result;
    }
    @Transactional void postPurchaseStep(UUID operation,long fence,String expected,String next,String step,String operationKey,Map<String,Object> result){
        int changed=jdbc.update("UPDATE post_purchase_operation SET current_step=?,status=?,lease_owner=NULL,lease_until=NULL,next_attempt_at=now(),last_error_code=NULL,updated_at=now() WHERE operation_id=? AND fence=? AND current_step=?",next,next.equals("DONE")?"COMPLETED":"RUNNING",operation,fence,expected);
        if(changed!=1)return;
        jdbc.update("INSERT INTO post_purchase_operation_step(operation_id,step,operation_key,state,result) VALUES (?,?,?,'SUCCEEDED',?::jsonb) ON CONFLICT(operation_id,step) DO UPDATE SET result=EXCLUDED.result,state='SUCCEEDED',updated_at=now()",operation,step,operationKey,OrdersJson.write(result));
        if(next.equals("DONE")){UUID order=jdbc.queryForObject("SELECT order_id FROM post_purchase_operation WHERE operation_id=?",UUID.class,operation);
            int changedOrder=jdbc.update("UPDATE customer_order SET state='CANCELLED',updated_at=now() WHERE id=? AND state='FULFILLMENT_SCHEDULED'",order);
            if(changedOrder!=1)throw new IllegalStateException("Order state changed before cancellation commit");
            var data=Map.of("orderId",order,"state","CANCELLED","operationId",operation,"refundMinor",result.get("refundMinor"),"currency",result.get("currency"),"reasonCode","CUSTOMER_REQUEST");
            eventWriter.appendPostPurchase(order,subject(order),"OrderCancelled",data);
        }
    }
    @Transactional void postPurchaseRetry(UUID operation,long fence,String code){jdbc.update("UPDATE post_purchase_operation SET status='RUNNING',lease_owner=NULL,lease_until=NULL,next_attempt_at=now()+least(interval '30 seconds',interval '1 second'*power(2,least(attempt,5))),last_error_code=?,updated_at=now() WHERE operation_id=? AND fence=?",code,operation,fence);}
    @Transactional void postPurchaseManualReview(UUID operation,long fence,String code){jdbc.update("UPDATE post_purchase_operation SET status='MANUAL_REVIEW',current_step='MANUAL_REVIEW',lease_owner=NULL,lease_until=NULL,last_error_code=?,updated_at=now() WHERE operation_id=? AND fence=?",code,operation,fence);}
    @Transactional void postPurchaseReject(UUID operation,long fence,String code){jdbc.update("UPDATE post_purchase_operation SET status='REJECTED',current_step='REJECTED',lease_owner=NULL,lease_until=NULL,last_error_code=?,updated_at=now() WHERE operation_id=? AND fence=?",code,operation,fence);}
    Map<String,Object> cancellationEligibility(UUID orderId,String subject){var rows=jdbc.queryForList("SELECT state FROM customer_order WHERE id=? AND customer_subject=?",orderId,subject);return rows.isEmpty()?null:Map.of("orderState",rows.getFirst().get("state"));}
    @Transactional(readOnly=true) Map<String,Object> cancellationReplay(UUID orderId,String subject,String key,String hash){var rows=jdbc.queryForList("SELECT operation_id,order_id,payload_hash,status,current_step FROM post_purchase_operation WHERE customer_subject=? AND idempotency_key=?",subject,key);if(rows.isEmpty())return null;var row=rows.getFirst();if(!orderId.equals(row.get("order_id"))||!hash.equals(row.get("payload_hash")))throw new IllegalStateException("IDEMPOTENCY_CONFLICT");var result=new java.util.LinkedHashMap<String,Object>();result.put("orderId",orderId);result.put("operationId",row.get("operation_id"));result.put("status",row.get("status"));result.put("currentStep",row.get("current_step"));result.put("replayed",true);return result;}
    Map<String,Object> cancellation(UUID orderId,UUID operationId,String subject){var rows=jdbc.queryForList("SELECT operation_id AS \"operationId\",order_id AS \"orderId\",status,current_step AS \"currentStep\",last_error_code AS \"errorCode\",created_at AS \"createdAt\",updated_at AS \"updatedAt\" FROM post_purchase_operation WHERE order_id=? AND operation_id=? AND customer_subject=?",orderId,operationId,subject);return rows.isEmpty()?null:rows.getFirst();}

    @Transactional(readOnly=true) Map<String,Object> returnReplay(UUID orderId,String subject,String key,String hash){
        var rows=jdbc.queryForList("SELECT return_id,order_id,payload_hash,status,current_step,amount_minor,currency FROM return_request WHERE customer_subject=? AND idempotency_key=?",subject,key);
        if(rows.isEmpty())return null;var row=rows.getFirst();if(!orderId.equals(row.get("order_id"))||!hash.equals(row.get("payload_hash")))throw new IllegalStateException("RETURN_IDEMPOTENCY_CONFLICT");return returnResponse(row);
    }

    @Transactional Map<String,Object> startReturn(UUID orderId,String subject,String key,String hash,Map<UUID,Integer> requested,Instant deliveredAt,long windowDays,long policyRevision){
        var orderRows=jdbc.queryForList("SELECT o.state,o.tax_minor,o.currency,s.fence FROM customer_order o JOIN checkout_saga s ON s.order_id=o.id WHERE o.id=? AND o.customer_subject=? FOR UPDATE OF o,s",orderId,subject);
        if(orderRows.isEmpty())return null;var order=orderRows.getFirst();
        var replay=jdbc.queryForList("SELECT return_id,order_id,payload_hash,status,current_step,amount_minor,currency FROM return_request WHERE customer_subject=? AND idempotency_key=? FOR UPDATE",subject,key);
        if(!replay.isEmpty()){var prior=replay.getFirst();if(!orderId.equals(prior.get("order_id"))||!hash.equals(prior.get("payload_hash")))throw new IllegalStateException("RETURN_IDEMPOTENCY_CONFLICT");return returnResponse(prior);}
        if(!ReturnRequestRules.withinWindow(deliveredAt,Instant.now(),windowDays))throw new IllegalStateException("RETURN_WINDOW_EXPIRED");
        var lineRows=jdbc.queryForList("SELECT sku_id,quantity,line_total_minor FROM customer_order_line WHERE order_id=? ORDER BY sku_id FOR UPDATE",orderId);
        var lines=lineRows.stream().map(row->new ReturnRefundAllocation.Line((UUID)row.get("sku_id"),((Number)row.get("quantity")).intValue(),((Number)row.get("line_total_minor")).longValue())).toList();
        var orderLines=new java.util.HashMap<UUID,ReturnRefundAllocation.Line>();lines.forEach(line->orderLines.put(line.skuId(),line));
        if(requested==null||requested.isEmpty()||requested.keySet().stream().anyMatch(sku->!orderLines.containsKey(sku)))throw new IllegalArgumentException("Return contains an unknown order line");
        var claimedRows=jdbc.queryForList("SELECT sku_id,count(*) AS quantity FROM return_unit_allocation WHERE order_id=? GROUP BY sku_id",orderId);
        var claimed=new java.util.HashMap<UUID,Integer>();claimedRows.forEach(row->claimed.put((UUID)row.get("sku_id"),((Number)row.get("quantity")).intValue()));
        requested.forEach((sku,quantity)->{if(quantity==null||quantity<1||claimed.getOrDefault(sku,0)+quantity>orderLines.get(sku).quantity())throw new IllegalStateException("RETURN_QUANTITY_EXCEEDED");});
        List<ReturnRefundAllocation.Unit> allocations=ReturnRefundAllocation.allocate(lines,((Number)order.get("tax_minor")).longValue(),claimed,requested);
        long amount=allocations.stream().mapToLong(ReturnRefundAllocation.Unit::refundMinor).reduce(0,Math::addExact);
        UUID returnId=UUID.randomUUID();long fence=jdbc.queryForObject("UPDATE checkout_saga SET fence=fence+1,updated_at=now() WHERE order_id=? RETURNING fence",Long.class,orderId);
        jdbc.update("INSERT INTO return_request(return_id,order_id,customer_subject,idempotency_key,payload_hash,status,current_step,amount_minor,currency,policy_revision,window_days,delivered_at,fence) VALUES (?,?,?, ?,?,'PENDING','REFUND',?,?,?,?,?,?)",returnId,orderId,subject,key,hash,amount,order.get("currency"),policyRevision,windowDays,Timestamp.from(deliveredAt),fence);
        for(var unit:allocations)jdbc.update("INSERT INTO return_unit_allocation(return_id,order_id,sku_id,unit_ordinal,merchandise_refund_minor,tax_refund_minor) VALUES (?,?,?,?,?,?)",returnId,orderId,unit.skuId(),unit.ordinal(),unit.merchandiseMinor(),unit.taxMinor());
        String state=order.get("state").toString();if(!"DELIVERED".equals(state)){
            if(!"FULFILLMENT_SCHEDULED".equals(state))throw new IllegalStateException("ORDER_NOT_RETURNABLE");
            jdbc.update("UPDATE customer_order SET state='DELIVERED',updated_at=now() WHERE id=?",orderId);
        }
        var requestedLines=requested.entrySet().stream().sorted(Map.Entry.comparingByKey()).map(entry->Map.of("skuId",entry.getKey().toString(),"quantity",entry.getValue())).toList();
        eventWriter.appendPostPurchase(orderId,subject,"OrderReturnRequested",Map.of("orderId",orderId,"state","DELIVERED","returnId",returnId,"lines",requestedLines,"policyRevision",policyRevision));
        var result=new java.util.LinkedHashMap<String,Object>();result.put("returnId",returnId);result.put("orderId",orderId);result.put("status","PENDING");result.put("currentStep","REFUND");result.put("amountMinor",amount);result.put("currency",order.get("currency"));result.put("policyRevision",policyRevision);return result;
    }

    @Transactional Map<String,Object> claimReturn(){
        var candidates=jdbc.queryForList("SELECT r.return_id,r.order_id,r.current_step FROM return_request r WHERE r.status IN ('PENDING','RUNNING') AND r.next_attempt_at<=now() AND (r.lease_until IS NULL OR r.lease_until<now()) AND NOT EXISTS (SELECT 1 FROM return_request earlier WHERE earlier.order_id=r.order_id AND earlier.status IN ('PENDING','RUNNING') AND (earlier.created_at,earlier.return_id)<(r.created_at,r.return_id)) ORDER BY r.created_at,r.return_id LIMIT 1 FOR UPDATE OF r SKIP LOCKED");
        if(candidates.isEmpty())return null;var row=candidates.getFirst();UUID order=(UUID)row.get("order_id"),returnId=(UUID)row.get("return_id");
        long fence=jdbc.queryForObject("UPDATE checkout_saga SET fence=fence+1,updated_at=now() WHERE order_id=? RETURNING fence",Long.class,order);
        jdbc.update("UPDATE return_request SET status='RUNNING',lease_owner=?,lease_until=now()+interval '30 seconds',fence=?,attempt=attempt+1,updated_at=now() WHERE return_id=?",UUID.randomUUID().toString(),fence,returnId);
        var details=jdbc.queryForList("SELECT amount_minor,currency,customer_subject FROM return_request WHERE return_id=?",returnId).getFirst();var result=new java.util.HashMap<String,Object>(row);result.putAll(details);result.put("fence",fence);return result;
    }
    @Transactional void retryReturn(UUID returnId,long fence,String code){jdbc.update("UPDATE return_request SET status='RUNNING',lease_owner=NULL,lease_until=NULL,next_attempt_at=now()+least(interval '30 seconds',interval '1 second'*power(2,least(attempt,5))),last_error_code=?,updated_at=now() WHERE return_id=? AND fence=?",code,returnId,fence);}
    @Transactional void manualReviewReturn(UUID returnId,long fence,String code){jdbc.update("UPDATE return_request SET status='MANUAL_REVIEW',current_step='MANUAL_REVIEW',lease_owner=NULL,lease_until=NULL,last_error_code=?,updated_at=now() WHERE return_id=? AND fence=?",code,returnId,fence);}
    @Transactional void completeReturn(UUID returnId,long fence){
        var rows=jdbc.queryForList("SELECT order_id,customer_subject,amount_minor,currency,status FROM return_request WHERE return_id=? FOR UPDATE",returnId);if(rows.isEmpty())return;var row=rows.getFirst();
        if("COMPLETED".equals(row.get("status")))return;
        int changed=jdbc.update("UPDATE return_request SET status='COMPLETED',current_step='DONE',lease_owner=NULL,lease_until=NULL,last_error_code=NULL,updated_at=now() WHERE return_id=? AND fence=? AND status='RUNNING'",returnId,fence);if(changed!=1)return;
        UUID order=(UUID)row.get("order_id");eventWriter.appendPostPurchase(order,row.get("customer_subject").toString(),"OrderRefundCompleted",Map.of("orderId",order,"state","DELIVERED","refundId",returnId,"amountMinor",row.get("amount_minor"),"currency",row.get("currency").toString().trim(),"reasonCode","RETURN"));
    }
    Map<String,Object> returnStatus(UUID orderId,UUID returnId,String subject){
        var rows=jdbc.queryForList("SELECT return_id AS \"returnId\",order_id AS \"orderId\",status,current_step AS \"currentStep\",amount_minor AS \"amountMinor\",currency,policy_revision AS \"policyRevision\",window_days AS \"windowDays\",delivered_at AS \"deliveredAt\",last_error_code AS \"errorCode\",created_at AS \"createdAt\",updated_at AS \"updatedAt\" FROM return_request WHERE order_id=? AND return_id=? AND customer_subject=?",orderId,returnId,subject);if(rows.isEmpty())return null;var result=new java.util.LinkedHashMap<String,Object>(rows.getFirst());result.put("lines",jdbc.queryForList("SELECT sku_id AS \"skuId\",count(*) AS quantity,sum(merchandise_refund_minor+tax_refund_minor) AS \"refundMinor\" FROM return_unit_allocation WHERE return_id=? GROUP BY sku_id ORDER BY sku_id",returnId));return result;
    }
    List<Map<String,Object>> returnableLines(UUID orderId,String subject){
        if(!ownsOrder(orderId,subject))return null;
        return jdbc.queryForList("SELECT l.sku_id AS \"skuId\",l.product_title AS \"productTitle\",l.quantity-COALESCE(a.claimed,0) AS \"returnableQuantity\",l.line_total_minor AS \"lineTotalMinor\" FROM customer_order_line l LEFT JOIN (SELECT sku_id,count(*) AS claimed FROM return_unit_allocation WHERE order_id=? GROUP BY sku_id) a ON a.sku_id=l.sku_id WHERE l.order_id=? ORDER BY l.sku_id",orderId,orderId);
    }
    private Map<String,Object> returnResponse(Map<String,Object> row){var result=new java.util.LinkedHashMap<String,Object>();result.put("returnId",row.get("return_id"));result.put("orderId",row.get("order_id"));result.put("status",row.get("status"));result.put("currentStep",row.get("current_step"));result.put("amountMinor",row.get("amount_minor"));result.put("currency",row.get("currency"));result.put("replayed",true);return result;}

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
        if(next.equals("DONE")){jdbc.update("UPDATE customer_order SET state='CONFIRMED',updated_at=now() WHERE id=?",id);jdbc.update("UPDATE checkout_saga SET state='FULFILLMENT_PENDING',current_step='SCHEDULE_FULFILLMENT' WHERE order_id=?",id);eventWriter.append(id,subject(id),"OrderConfirmed",Map.of("orderId",id,"state","CONFIRMED"));}
        if(next.equals("FULFILLMENT_DONE")){jdbc.update("UPDATE customer_order SET state='FULFILLMENT_SCHEDULED',updated_at=now() WHERE id=?",id);jdbc.update("UPDATE checkout_saga SET state='COMPLETED',current_step='COMPLETED' WHERE order_id=?",id);eventWriter.append(id,subject(id),"FulfillmentScheduled",Map.of("orderId",id,"state","FULFILLMENT_SCHEDULED"));}
    }
    @Transactional void sagaRetry(UUID id,long fence,String code){jdbc.update("UPDATE checkout_saga SET lease_owner=NULL,lease_until=NULL,next_attempt_at=now()+least(interval '30 seconds', interval '1 second' * power(2,least(attempt,5))),last_error_code=?,updated_at=now() WHERE order_id=? AND fence=?",code,id,fence);}
    @Transactional void failDeclined(UUID id,long fence){int changed=jdbc.update("UPDATE checkout_saga SET state='FAILED',current_step='FAILED',lease_owner=NULL,lease_until=NULL,last_error_code='PAYMENT_DECLINED',updated_at=now() WHERE order_id=? AND fence=? AND current_step='AUTHORIZE'",id,fence);if(changed==1){jdbc.update("UPDATE customer_order SET state='FAILED',updated_at=now() WHERE id=?",id);jdbc.update("INSERT INTO checkout_saga_step(order_id,step,operation_key,state,error_code) VALUES (?,'PAYMENT_DECLINED',?,'FAILED','PAYMENT_DECLINED') ON CONFLICT(order_id,step) DO UPDATE SET state='FAILED',error_code='PAYMENT_DECLINED',updated_at=now()",id,id+":payment-declined");eventWriter.append(id,subject(id),"OrderPaymentDeclined",Map.of("orderId",id,"state","FAILED","reason","PAYMENT_DECLINED"));}}
    @Transactional void failExpiredQuote(UUID id,long fence){int changed=jdbc.update("UPDATE checkout_saga SET state='FAILED',current_step='FAILED',lease_owner=NULL,lease_until=NULL,last_error_code='QUOTE_EXPIRED',updated_at=now() WHERE order_id=? AND fence=? AND current_step='RESERVE_INVENTORY'",id,fence);if(changed==1){jdbc.update("UPDATE customer_order SET state='FAILED',updated_at=now() WHERE id=?",id);jdbc.update("INSERT INTO checkout_saga_step(order_id,step,operation_key,state,error_code) VALUES (?,'QUOTE_EXPIRED',?,'FAILED','QUOTE_EXPIRED') ON CONFLICT(order_id,step) DO UPDATE SET state='FAILED',error_code='QUOTE_EXPIRED',updated_at=now()",id,id+":quote-expired");eventWriter.append(id,subject(id),"OrderCheckoutExpired",Map.of("orderId",id,"state","FAILED","reason","QUOTE_EXPIRED"));}}
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
        var eventData=new java.util.LinkedHashMap<String,Object>();eventData.put("orderId",orderId);eventData.put("checkoutRequestId",requestId);eventData.put("state","PENDING_PAYMENT");eventData.put("currency",currency);eventData.put("subtotalMinor",subtotal);eventData.put("discountMinor",discount);eventData.put("taxMinor",tax);eventData.put("shippingMinor",shipping);eventData.put("totalMinor",total);eventData.put("lines",jdbc.queryForList("SELECT sku_id AS \"skuId\",product_id AS \"productId\",product_title AS \"productTitle\",quantity,unit_price_minor AS \"unitPriceMinor\",discount_minor AS \"discountMinor\",line_total_minor AS \"lineTotalMinor\",currency FROM customer_order_line WHERE order_id=? ORDER BY sku_id",orderId));eventWriter.append(orderId,subject,"OrderAccepted",eventData);
        jdbc.update("UPDATE checkout_request SET status='ACCEPTED',order_id=?,error_code=NULL,updated_at=now() WHERE id=?",orderId,requestId);
        return Map.of("requestId",requestId,"orderId",orderId,"status","ACCEPTED","state","PENDING_PAYMENT","currency",currency,"subtotalMinor",subtotal,"discountMinor",discount,"taxMinor",tax,"shippingMinor",shipping,"totalMinor",total);
    }
    @Transactional void reject(UUID requestId,String code){jdbc.update("UPDATE checkout_request SET status='REJECTED',error_code=?,updated_at=now() WHERE id=? AND status='VALIDATING'",code,requestId);}
    private String subject(UUID orderId){return jdbc.queryForObject("SELECT customer_subject FROM customer_order WHERE id=?",String.class,orderId);}
    Map<String,Object> request(UUID id,String subject) {
        List<Map<String,Object>> rows=jdbc.queryForList("SELECT id,status,order_id,error_code,created_at,updated_at FROM checkout_request WHERE id=? AND customer_subject=?",id,subject);
        return rows.isEmpty()?null:rows.getFirst();
    }
    List<Map<String,Object>> orders(String subject) {
        return jdbc.queryForList("SELECT id,state,currency,subtotal_minor AS \"subtotalMinor\",discount_minor AS \"discountMinor\",tax_minor AS \"taxMinor\",shipping_minor AS \"shippingMinor\",total_minor AS \"totalMinor\",created_at AS \"createdAt\" FROM customer_order WHERE customer_subject=? ORDER BY created_at DESC LIMIT 100",subject);
    }
    boolean ownsOrder(UUID id,String subject){return Boolean.TRUE.equals(jdbc.queryForObject("SELECT EXISTS(SELECT 1 FROM customer_order WHERE id=? AND customer_subject=?)",Boolean.class,id,subject));}
    Map<String,Object> order(UUID id,String subject) {
        var rows=jdbc.queryForList("SELECT id,state,currency,subtotal_minor AS \"subtotalMinor\",discount_minor AS \"discountMinor\",tax_minor AS \"taxMinor\",shipping_minor AS \"shippingMinor\",total_minor AS \"totalMinor\",address_snapshot AS \"addressSnapshot\",quote_snapshot AS \"quoteSnapshot\",created_at AS \"createdAt\" FROM customer_order WHERE id=? AND customer_subject=?",id,subject);
        if(rows.isEmpty())return null;var result=new java.util.HashMap<>(rows.getFirst());result.put("addressSnapshot",OrdersJson.readMap(result.get("addressSnapshot")));result.put("quoteSnapshot",OrdersJson.readMap(result.get("quoteSnapshot")));result.put("lines",jdbc.queryForList("SELECT sku_id AS \"skuId\",product_id AS \"productId\",product_title AS \"productTitle\",quantity,unit_price_minor AS \"unitPriceMinor\",discount_minor AS \"discountMinor\",line_total_minor AS \"lineTotalMinor\",currency FROM customer_order_line WHERE order_id=? ORDER BY sku_id",id));return result;
    }
}
