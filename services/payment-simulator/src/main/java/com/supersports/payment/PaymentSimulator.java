package com.supersports.payment;

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
    Map<String,Object> execute(UUID orderId, String operation, String key, long fence, long amount, String currency, String mode) {
        if (fence < 1 || amount < 0 || !currency.matches("[A-Z]{3}")) throw new IllegalArgumentException("Invalid payment operation");
        jdbc.update("INSERT INTO payment_fence(order_id,fence) VALUES (?,?) ON CONFLICT(order_id) DO UPDATE SET fence=EXCLUDED.fence WHERE payment_fence.fence < EXCLUDED.fence", orderId, fence);
        Long current = jdbc.queryForObject("SELECT fence FROM payment_fence WHERE order_id=? FOR UPDATE", Long.class, orderId);
        if (current == null || current != fence) throw new StaleFenceException();
        String payload = operation + ":" + amount + ":" + currency + ":" + mode;
        var existing = jdbc.queryForList("SELECT payload_hash,state,operation_key FROM payment_operation WHERE operation_key=?", key);
        if (!existing.isEmpty()) {
            if (!payload.equals(existing.getFirst().get("payload_hash"))) throw new OperationConflictException();
            return Map.of("orderId", orderId, "operationKey", key, "state", existing.getFirst().get("state"), "replayed", true);
        }
        String state = switch (operation) {
            case "AUTHORIZE" -> mode.equals("DECLINE") ? "DECLINED" : "AUTHORIZED";
            case "CAPTURE" -> requirePrior(orderId, "AUTHORIZED") ? "CAPTURED" : throwState();
            case "VOID" -> requirePrior(orderId, "AUTHORIZED") ? "VOIDED" : throwState();
            case "REFUND" -> requirePrior(orderId, "CAPTURED") ? "REFUNDED" : throwState();
            default -> throw new IllegalArgumentException("Unsupported payment operation");
        };
        jdbc.update("INSERT INTO payment_operation(order_id,operation,operation_key,payload_hash,amount_minor,currency,state,fence) VALUES (?,?,?,?,?,?,?,?)", orderId, operation, key, payload, amount, currency, state, fence);
        return Map.of("orderId", orderId, "operationKey", key, "state", state, "replayed", false);
    }
    private boolean requirePrior(UUID id, String state) { return jdbc.queryForObject("SELECT count(*) FROM payment_operation WHERE order_id=? AND state=?", Integer.class, id, state) > 0; }
    private String throwState() { throw new IllegalStateException("Payment state does not permit this operation"); }
    Map<String,Object> status(UUID orderId) { var rows=jdbc.queryForList("SELECT operation,operation_key AS \"operationKey\",amount_minor AS \"amountMinor\",currency,state FROM payment_operation WHERE order_id=? ORDER BY id",orderId);return Map.of("orderId",orderId,"operations",rows); }
    static final class StaleFenceException extends RuntimeException {}
    static final class OperationConflictException extends RuntimeException {}
}
