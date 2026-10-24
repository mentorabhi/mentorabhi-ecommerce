package com.supersports.orderhistory;

import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;
import org.springframework.transaction.support.TransactionTemplate;

@Component
class ReplayOperations {
    private final JdbcTemplate jdbc;
    private final TransactionTemplate tx;
    private final OperatorKafka kafka;
    private final String topic, dlq;

    ReplayOperations(JdbcTemplate jdbc, TransactionTemplate tx, OperatorKafka kafka,
                     @Value("${order-history.topic}") String topic, @Value("${order-history.dlq-topic}") String dlq) {
        this.jdbc=jdbc; this.tx=tx; this.kafka=kafka; this.topic=topic; this.dlq=dlq;
    }

    Map<String,Object> demo() {
        var valid = new ArrayList<ConsumerRecord<String,String>>();
        kafka.scan(topic, record -> {
            try {
                var event=HistoryRules.parse(EventContent.read(record.value()));
                Long count=jdbc.queryForObject("SELECT count(*) FROM event_inbox WHERE event_id=?",Long.class,event.eventId());
                if (count!=null && count==1 && valid.isEmpty()) valid.add(record);
            } catch (IllegalArgumentException ignored) { }
        });
        if (valid.isEmpty()) throw new IllegalArgumentException("DEMO_REQUIRES_PROJECTED_ORDER");
        var source=valid.getFirst();
        var corrupt=EventContent.read(source.value());corrupt.put("eventVersion",999);
        var published=kafka.publish(topic,source.partition(),source.key(),EventContent.write(corrupt));
        String coordinate=topic+":"+published.partition()+":"+published.offset();
        long deadline=System.nanoTime()+Duration.ofSeconds(60).toNanos();
        while (System.nanoTime()<deadline) {
            if (deadLetter(coordinate)!=null) return Map.of("sourceCoordinate",coordinate,"correctedPayload",source.value(),"operationId",UUID.randomUUID().toString());
            try { Thread.sleep(500); } catch (InterruptedException error) { Thread.currentThread().interrupt(); throw new IllegalStateException("DEMO_INTERRUPTED"); }
        }
        throw new IllegalStateException("DEMO_DLQ_TIMEOUT");
    }

    Map<String,Object> replay(Map<String,Object> request, String operator) {
        UUID operation;
        try { operation=UUID.fromString(text(request,"operationId")); } catch (RuntimeException error) { throw new IllegalArgumentException("INVALID_REPLAY_OPERATION_ID"); }
        String coordinate=text(request,"sourceCoordinate");
        var source=ReplayRules.coordinate(coordinate,topic);
        String corrected=text(request,"correctedPayload"), reason=text(request,"reason");
        if (reason.length()>500 || operator.length()>160) throw new IllegalArgumentException("INVALID_REPLAY_AUDIT_FIELDS");
        var event=HistoryRules.parse(EventContent.read(corrected));
        String hash=EventContent.hash(corrected);
        var prior=receipt(operation);
        if (!prior.isEmpty()) checkSame(prior,coordinate,hash,operator,reason);
        else {
            var original=deadLetter(coordinate);
            if (original==null) throw new IllegalArgumentException("DLQ_COORDINATE_NOT_FOUND");
            ReplayRules.correction(original.value(),corrected);
            assertAppliedContent(event.eventId(),corrected);
            var originalKey=original.headers().lastHeader("source-key");
            String key=originalKey==null?event.aggregateId().toString():new String(originalKey.value(),StandardCharsets.UTF_8);
            tx.executeWithoutResult(status -> {
                jdbc.query("SELECT pg_advisory_xact_lock(hashtextextended(?,0))",rs->{},operation.toString());
                var concurrent=receipt(operation);
                if (!concurrent.isEmpty()) { checkSame(concurrent,coordinate,hash,operator,reason); return; }
                jdbc.update("INSERT INTO order_history_replay_audit(operation_id,source_coordinate,event_id,original_payload_hash,replay_payload_hash,operator_subject,reason) VALUES (?,?,?,?,?,?,?)",operation,coordinate,event.eventId(),EventContent.rawHash(original.value()),hash,operator,reason);
                jdbc.update("INSERT INTO order_history_replay_delivery(operation_id,corrected_payload,source_partition,record_key) VALUES (?,?,?,?)",operation,corrected,source.partition(),key);
            });
        }
        var delivery=receipt(operation);
        if (delivery.get("publishedOffset")==null) {
            if (Boolean.TRUE.equals(request.get("failBeforePublish"))) throw new IllegalStateException("INJECTED_BEFORE_PUBLISH");
            var published=kafka.publish(topic,((Number)delivery.get("sourcePartition")).intValue(),(String)delivery.get("recordKey"),(String)delivery.get("correctedPayload"));
            if (Boolean.TRUE.equals(request.get("failAfterPublish"))) throw new IllegalStateException("INJECTED_AFTER_PUBLISH");
            jdbc.update("UPDATE order_history_replay_delivery SET published_topic=?,published_partition=?,published_offset=?,published_at=now() WHERE operation_id=? AND published_at IS NULL",published.topic(),published.partition(),published.offset(),operation);
            delivery=receipt(operation);
        }
        return Map.of("operationId",operation.toString(),"sourceCoordinate",coordinate,"eventId",event.eventId().toString(),"status","PUBLISHED","topic",delivery.get("publishedTopic"),"partition",delivery.get("publishedPartition"),"offset",delivery.get("publishedOffset"));
    }

    private void assertAppliedContent(UUID eventId, String corrected) {
        var rows=jdbc.query("SELECT payload_hash,canonical_payload_hash FROM event_inbox WHERE event_id=?",(rs,n)->new HistoryProjector.Fingerprint(rs.getString(1),rs.getString(2)),eventId);
        if (rows.isEmpty()) return;
        var fingerprint=rows.getFirst();String canonical=EventContent.hash(corrected);
        if (fingerprint.matches(EventContent.rawHash(corrected),canonical)) return;
        if (fingerprint.canonical()==null) {
            var matches=new ArrayList<String>();
            kafka.scan(topic,record -> {
                if (fingerprint.raw().equals(EventContent.rawHash(record.value())) && canonical.equals(EventContent.hash(record.value()))) matches.add(canonical);
            });
            if (!matches.isEmpty()) {
                jdbc.update("UPDATE event_inbox SET canonical_payload_hash=? WHERE event_id=? AND canonical_payload_hash IS NULL",canonical,eventId);
                return;
            }
        }
        throw new IllegalArgumentException("APPLIED_EVENT_CANNOT_BE_REWRITTEN");
    }

    private ConsumerRecord<String,String> deadLetter(String coordinate) {
        var matches=new ArrayList<ConsumerRecord<String,String>>();
        kafka.scan(dlq,record -> { if (coordinate.equals(record.key())) matches.add(record); });
        if (matches.isEmpty()) return null;
        String originalHash=EventContent.rawHash(matches.getFirst().value());
        if (matches.stream().anyMatch(record -> !originalHash.equals(EventContent.rawHash(record.value())))) throw new IllegalArgumentException("DLQ_COORDINATE_CONFLICT");
        return matches.getFirst();
    }

    private Map<String,Object> receipt(UUID operation) {
        var rows=jdbc.queryForList("SELECT a.source_coordinate AS \"sourceCoordinate\",a.replay_payload_hash AS hash,a.operator_subject AS operator,a.reason,d.corrected_payload AS \"correctedPayload\",d.source_partition AS \"sourcePartition\",d.record_key AS \"recordKey\",d.published_topic AS \"publishedTopic\",d.published_partition AS \"publishedPartition\",d.published_offset AS \"publishedOffset\" FROM order_history_replay_audit a JOIN order_history_replay_delivery d USING(operation_id) WHERE a.operation_id=?",operation);
        return rows.isEmpty()?Map.of():rows.getFirst();
    }

    private static void checkSame(Map<String,Object> row,String coordinate,String hash,String operator,String reason) {
        if (!coordinate.equals(row.get("sourceCoordinate")) || !hash.equals(row.get("hash")) || !operator.equals(row.get("operator")) || !reason.equals(row.get("reason"))) throw new IllegalArgumentException("REPLAY_OPERATION_ID_CONFLICT");
    }
    private static String text(Map<String,Object> request,String key) {
        Object value=request.get(key);if (!(value instanceof String text) || text.isBlank()) throw new IllegalArgumentException("INVALID_OPERATOR_REQUEST");return text;
    }
}
