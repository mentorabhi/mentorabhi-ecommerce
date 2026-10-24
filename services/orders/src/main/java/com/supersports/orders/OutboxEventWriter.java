package com.supersports.orders;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Instant;
import java.sql.Timestamp;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

@Component
class OutboxEventWriter {
    private final JdbcTemplate jdbc;
    private final byte[] ownerKey;
    private volatile boolean backfillComplete;

    OutboxEventWriter(JdbcTemplate jdbc, @Value("${order-history.owner-key}") String ownerKey) {
        this.jdbc = jdbc;
        this.ownerKey = ownerKey.getBytes(StandardCharsets.UTF_8);
        if (ownerKey.length() < 32) throw new IllegalArgumentException("Order History ownership key must contain at least 32 characters");
    }

    String customerKey(String subject) {
        try {
            Mac mac=Mac.getInstance("HmacSHA256");mac.init(new SecretKeySpec(ownerKey,"HmacSHA256"));
            return java.util.HexFormat.of().formatHex(mac.doFinal(subject.getBytes(StandardCharsets.UTF_8)));
        } catch (java.security.GeneralSecurityException e) { throw new IllegalStateException("Could not derive customer ownership key",e); }
    }

    void append(UUID orderId,String subject,String eventType,Map<String,Object> data) {
        if(!backfillComplete)throw new IllegalStateException("Order outbox legacy backfill is not complete");
        Long sequence=jdbc.queryForObject("INSERT INTO order_event_sequence(aggregate_id,last_sequence) VALUES (?,1) ON CONFLICT (aggregate_id) DO UPDATE SET last_sequence=order_event_sequence.last_sequence+1 RETURNING last_sequence",Long.class,orderId);
        UUID eventId=UUID.randomUUID();String customerKey=customerKey(subject);Instant occurredAt=Instant.now();
        Map<String,Object> envelope=new LinkedHashMap<>();envelope.put("eventId",eventId);envelope.put("eventType",eventType);envelope.put("eventVersion",1);envelope.put("aggregateType","Order");envelope.put("aggregateId",orderId);envelope.put("aggregateSequence",sequence);envelope.put("occurredAt",occurredAt.toString());envelope.put("customerKey",customerKey);envelope.put("data",data);
        jdbc.update("INSERT INTO order_outbox(aggregate_id,aggregate_type,event_type,payload,event_id,event_version,aggregate_sequence,customer_key,created_at) VALUES (?,'Order',?,?::jsonb,?,?,?,?,?)",orderId,eventType,OrdersJson.write(envelope),eventId,1,sequence,customerKey,Timestamp.from(occurredAt));
    }

    void enableAfterBackfill(){backfillComplete=true;}

    static UUID legacyEventId(long outboxId) {
        try {
            UUID namespace=UUID.fromString("f58b4f4d-cb87-5df1-8a9d-7fcd6d8d3554");
            var bytes=java.nio.ByteBuffer.allocate(16).putLong(namespace.getMostSignificantBits()).putLong(namespace.getLeastSignificantBits()).array();
            MessageDigest sha1=MessageDigest.getInstance("SHA-1");sha1.update(bytes);byte[] hash=sha1.digest(("supersports-order-outbox:"+outboxId).getBytes(StandardCharsets.UTF_8));
            hash[6]=(byte)((hash[6]&0x0f)|0x50);hash[8]=(byte)((hash[8]&0x3f)|0x80);
            var buffer=java.nio.ByteBuffer.wrap(hash);return new UUID(buffer.getLong(),buffer.getLong());
        } catch (java.security.NoSuchAlgorithmException e) { throw new IllegalStateException(e); }
    }
}
