package com.supersports.fulfillment;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.HexFormat;
import java.util.Map;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

@Repository
class FulfillmentRepository {
    private final JdbcTemplate jdbc;

    FulfillmentRepository(JdbcTemplate jdbc){this.jdbc=jdbc;}

    @Transactional
    Map<String,Object> schedule(UUID order,long fence,String key){
        if(fence<1)throw new IllegalArgumentException("Fence must be positive");
        jdbc.update("INSERT INTO fulfillment_fence(order_id,fence) VALUES (?,?) ON CONFLICT(order_id) DO UPDATE SET fence=EXCLUDED.fence WHERE fulfillment_fence.fence < EXCLUDED.fence",order,fence);
        Long current=jdbc.queryForObject("SELECT fence FROM fulfillment_fence WHERE order_id=? FOR UPDATE",Long.class,order);
        if(current==null||current!=fence)throw new StaleFenceException();
        var prior=jdbc.queryForList("SELECT order_id,tracking_id,state,revision,estimated_delivery_at FROM shipment WHERE operation_key=?",key);
        if(!prior.isEmpty()){
            if(!order.equals(prior.getFirst().get("order_id")))throw new IllegalStateException("Operation key belongs to another order");
            return shipmentResponse(prior.getFirst(),true);
        }
        String tracking="SS-"+order.toString().substring(0,8).toUpperCase();
        Instant estimatedDelivery=Instant.now().plusSeconds(4*24*60*60L);
        jdbc.update("INSERT INTO shipment(order_id,operation_key,tracking_id,fence,state,estimated_delivery_at) VALUES (?,?,?,?,'SCHEDULED',?)",
            order,key,tracking,fence,Timestamp.from(estimatedDelivery));
        return Map.of("orderId",order,"trackingId",tracking,"state","SCHEDULED","revision",0L,
            "estimatedDeliveryAt",estimatedDelivery,"replayed",false);
    }

    @Transactional
    Map<String,Object> advance(UUID order,long expectedRevision,UUID operationId,String target,String reason,String actor){
        if(expectedRevision<0)throw new IllegalArgumentException("Invalid expected revision");
        if(target==null||reason==null||reason.isBlank()||reason.length()>500||actor==null||actor.isBlank()||actor.length()>160)
            throw new IllegalArgumentException("Invalid transition fields");
        String fingerprint=hash(order+"|"+expectedRevision+"|"+target+"|"+reason+"|"+actor);
        jdbc.query("SELECT pg_advisory_xact_lock(hashtextextended(?,0))",rs->{},operationId.toString());
        var prior=jdbc.queryForList("SELECT operation_id,order_id,request_hash,previous_state,next_state,previous_revision,next_revision,actor_subject,reason,created_at FROM shipment_transition_audit WHERE operation_id=?",operationId);
        if(!prior.isEmpty()){
            var audit=prior.getFirst();
            if(!order.equals(audit.get("order_id"))||!fingerprint.equals(audit.get("request_hash").toString().trim()))throw new OperationConflictException();
            return transitionResponse(order,audit,true);
        }
        var rows=jdbc.queryForList("SELECT order_id,tracking_id,state,revision,estimated_delivery_at FROM shipment WHERE order_id=? FOR UPDATE",order);
        if(rows.isEmpty())throw new ShipmentNotFoundException();
        var shipment=rows.getFirst();
        long revision=((Number)shipment.get("revision")).longValue();
        if(revision!=expectedRevision)throw new StaleRevisionException();
        String state=shipment.get("state").toString();
        if(!ShipmentTransitionRules.permits(state,target))throw new InvalidTransitionException();
        long nextRevision=revision+1;
        int changed=jdbc.update("UPDATE shipment SET state=?,revision=? WHERE order_id=? AND revision=?",target,nextRevision,order,revision);
        if(changed!=1)throw new StaleRevisionException();
        Instant created=Instant.now();
        jdbc.update("INSERT INTO shipment_transition_audit(operation_id,order_id,request_hash,previous_state,next_state,previous_revision,next_revision,actor_subject,reason,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            operationId,order,fingerprint,state,target,revision,nextRevision,actor,reason,Timestamp.from(created));
        return Map.of("orderId",order,"trackingId",shipment.get("tracking_id"),"previousState",state,"state",target,
            "previousRevision",revision,"revision",nextRevision,"estimatedDeliveryAt",shipment.get("estimated_delivery_at"),
            "operationId",operationId,"actorSubject",actor,"reason",reason,"createdAt",created,"replayed",false);
    }

    Map<String,Object> status(UUID order){
        var rows=jdbc.queryForList("SELECT order_id AS \"orderId\",tracking_id AS \"trackingId\",state,revision,created_at AS \"scheduledAt\",estimated_delivery_at AS \"estimatedDeliveryAt\" FROM shipment WHERE order_id=?",order);
        if(rows.isEmpty())return Map.of("orderId",order,"state","PENDING");
        var response=new java.util.LinkedHashMap<String,Object>(rows.getFirst());
        response.put("transitions",jdbc.queryForList("SELECT operation_id AS \"operationId\",previous_state AS \"previousState\",next_state AS state,previous_revision AS \"previousRevision\",next_revision AS revision,actor_subject AS \"actorSubject\",reason,created_at AS \"createdAt\" FROM shipment_transition_audit WHERE order_id=? ORDER BY next_revision",order));
        return response;
    }

    @Transactional
    Map<String,Object> claimCancellation(UUID order,long expectedRevision,UUID operationId){
        var rows=jdbc.queryForList("SELECT state,revision,cancel_claim_operation_id FROM shipment WHERE order_id=? FOR UPDATE",order);
        if(rows.isEmpty())throw new ShipmentNotFoundException();var row=rows.getFirst();
        if(row.get("cancel_claim_operation_id")!=null){
            if(operationId.equals(row.get("cancel_claim_operation_id")))return Map.of("orderId",order,"state",row.get("state"),"revision",row.get("revision"),"replayed",true);
            throw new InvalidTransitionException();
        }
        if(!"SCHEDULED".equals(row.get("state"))||((Number)row.get("revision")).longValue()!=expectedRevision)throw new StaleRevisionException();
        long next=expectedRevision+1;
        jdbc.update("UPDATE shipment SET state='CANCEL_CLAIMED',revision=?,cancel_claim_operation_id=? WHERE order_id=? AND revision=?",next,operationId,order,expectedRevision);
        jdbc.update("INSERT INTO shipment_cancellation_audit(operation_id,order_id,action,previous_state,next_state,previous_revision,next_revision) VALUES (?,?,'CLAIM','SCHEDULED','CANCEL_CLAIMED',?,?)",operationId,order,expectedRevision,next);
        return Map.of("orderId",order,"state","CANCEL_CLAIMED","revision",next,"replayed",false);
    }

    @Transactional
    Map<String,Object> finalizeCancellation(UUID order,UUID claimId,UUID operationId){
        var rows=jdbc.queryForList("SELECT state,revision,cancel_claim_operation_id,cancellation_operation_id FROM shipment WHERE order_id=? FOR UPDATE",order);
        if(rows.isEmpty())throw new ShipmentNotFoundException();var row=rows.getFirst();
        if(operationId.equals(row.get("cancellation_operation_id")))return Map.of("orderId",order,"state","CANCELLED","revision",row.get("revision"),"replayed",true);
        if(!"CANCEL_CLAIMED".equals(row.get("state"))||!claimId.equals(row.get("cancel_claim_operation_id"))||row.get("cancellation_operation_id")!=null)throw new InvalidTransitionException();
        long previous=((Number)row.get("revision")).longValue(),next=previous+1;
        jdbc.update("UPDATE shipment SET state='CANCELLED',revision=?,cancellation_operation_id=? WHERE order_id=? AND revision=?",next,operationId,order,previous);
        jdbc.update("INSERT INTO shipment_cancellation_audit(operation_id,order_id,action,previous_state,next_state,previous_revision,next_revision) VALUES (?,?,'CANCEL','CANCEL_CLAIMED','CANCELLED',?,?)",operationId,order,previous,next);
        return Map.of("orderId",order,"state","CANCELLED","revision",next,"replayed",false);
    }

    private Map<String,Object> shipmentResponse(Map<String,Object> row,boolean replayed){
        return Map.of("orderId",row.get("order_id"),"trackingId",row.get("tracking_id"),"state",row.get("state"),
            "revision",row.get("revision"),"estimatedDeliveryAt",row.get("estimated_delivery_at"),"replayed",replayed);
    }
    private Map<String,Object> transitionResponse(UUID order,Map<String,Object> audit,boolean replayed){
        var rows=jdbc.queryForList("SELECT tracking_id,estimated_delivery_at FROM shipment WHERE order_id=?",order);
        if(rows.isEmpty())throw new ShipmentNotFoundException();
        var row=rows.getFirst();
        return Map.of("orderId",order,"trackingId",row.get("tracking_id"),"previousState",audit.get("previous_state"),"state",audit.get("next_state"),
            "previousRevision",audit.get("previous_revision"),"revision",audit.get("next_revision"),"estimatedDeliveryAt",row.get("estimated_delivery_at"),
            "operationId",audit.get("operation_id"),"actorSubject",audit.get("actor_subject"),"reason",audit.get("reason"),
            "createdAt",audit.get("created_at"),"replayed",replayed);
    }
    private static String hash(String value){
        try{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8)));}
        catch(Exception error){throw new IllegalStateException("SHA-256 is unavailable",error);}
    }
    private static class StaleFenceException extends RuntimeException{}
    static class StaleRevisionException extends RuntimeException{}
    static class OperationConflictException extends RuntimeException{}
    static class InvalidTransitionException extends RuntimeException{}
    static class ShipmentNotFoundException extends RuntimeException{}
}
