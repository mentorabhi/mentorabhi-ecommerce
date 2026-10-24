package com.supersports.payment;

import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

@Repository
class PaymentSimulator {
    private final JdbcTemplate jdbc;
    PaymentSimulator(JdbcTemplate jdbc) { this.jdbc = jdbc; }

    @Transactional
    Map<String,Object> execute(UUID orderId,String operation,String key,long fence,long amount,String currency,String mode) {
        if(orderId==null||key==null||key.isBlank()||key.length()>200||fence<1||amount<0||currency==null||!currency.matches("[A-Z]{3}"))
            throw new IllegalArgumentException("Invalid payment operation");
        String normalized=operation==null?"":operation.toUpperCase(java.util.Locale.ROOT);
        String authorizationMode=mode==null?"":mode.toUpperCase(java.util.Locale.ROOT);
        if(!List.of("AUTHORIZE","CAPTURE","VOID","REFUND").contains(normalized))throw new IllegalArgumentException("Unsupported payment operation");
        if(!List.of("APPROVE","DECLINE").contains(authorizationMode))throw new IllegalArgumentException("Invalid authorization mode");

        jdbc.update("INSERT INTO payment_fence(order_id,fence) VALUES (?,?) ON CONFLICT(order_id) DO UPDATE SET fence=EXCLUDED.fence WHERE payment_fence.fence < EXCLUDED.fence",orderId,fence);
        Long current=jdbc.queryForObject("SELECT fence FROM payment_fence WHERE order_id=? FOR UPDATE",Long.class,orderId);
        if(current==null||current!=fence)throw new StaleFenceException();

        String payload=normalized+":"+amount+":"+currency+":"+authorizationMode;
        var prior=findOperation(key);
        if(prior!=null)return replayOrConflict(prior,orderId,payload,key);

        var facts=jdbc.queryForList("SELECT operation,amount_minor,currency,state FROM payment_operation WHERE order_id=? ORDER BY id",orderId)
                .stream().map(row->new PaymentLedgerRules.Fact(row.get("operation").toString(),((Number)row.get("amount_minor")).longValue(),row.get("currency").toString().trim(),row.get("state").toString())).toList();
        String state=PaymentLedgerRules.decide(normalized,amount,currency,authorizationMode,facts);
        int inserted=jdbc.update("INSERT INTO payment_operation(order_id,operation,operation_key,payload_hash,amount_minor,currency,state,fence) VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(operation_key) DO NOTHING",
                orderId,normalized,key,payload,amount,currency,state,fence);
        if(inserted==0){var winner=findOperation(key);if(winner==null)throw new IllegalStateException("Payment operation was concurrently claimed");return replayOrConflict(winner,orderId,payload,key);}
        return Map.of("orderId",orderId,"operationKey",key,"state",state,"replayed",false);
    }

    private Map<String,Object> replayOrConflict(Map<String,Object> existing,UUID orderId,String payload,String key){
        if(!orderId.toString().equals(existing.get("order_id").toString())||!payload.equals(existing.get("payload_hash")))throw new OperationConflictException();
        return Map.of("orderId",orderId,"operationKey",key,"state",existing.get("state"),"replayed",true);
    }
    private Map<String,Object> findOperation(String key){
        var rows=jdbc.queryForList("SELECT order_id,payload_hash,state FROM payment_operation WHERE operation_key=?",key);
        return rows.isEmpty()?null:rows.getFirst();
    }
    Map<String,Object> status(UUID orderId){var rows=jdbc.queryForList("SELECT operation,operation_key AS \"operationKey\",amount_minor AS \"amountMinor\",currency,state FROM payment_operation WHERE order_id=? ORDER BY id",orderId);return Map.of("orderId",orderId,"operations",rows);}
    static final class StaleFenceException extends RuntimeException {}
    static final class OperationConflictException extends RuntimeException {}
}
