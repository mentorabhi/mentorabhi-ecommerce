package com.supersports.orderhistory;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;
import org.springframework.transaction.support.TransactionTemplate;
import tools.jackson.databind.json.JsonMapper;

@Component
class HistoryProjector {
    private final JdbcTemplate jdbc;private final TransactionTemplate tx;private final JsonMapper json=new JsonMapper();
    HistoryProjector(JdbcTemplate jdbc,TransactionTemplate tx){this.jdbc=jdbc;this.tx=tx;}

    Outcome project(String raw,String topic,int partition,long offset){
        Map<String,Object> envelope;
        try{envelope=json.readValue(raw,Map.class);}catch(Exception e){throw new PoisonEventException("INVALID_JSON",e);}
        final HistoryRules.Event event;
        try{event=HistoryRules.parse(envelope);}catch(RuntimeException e){throw new PoisonEventException("INVALID_EVENT",e);}
        String hash=sha256(raw);
        String canonicalHash=EventContent.hash(raw);
        try{return tx.execute(status->projectTransaction(event,envelope,hash,canonicalHash,topic,partition,offset));}
        catch(PoisonEventException e){throw e;}catch(RuntimeException e){throw e;}
    }

    UUID aggregateId(String raw){
        try{return HistoryRules.parse(read(raw)).aggregateId();}
        catch(RuntimeException e){throw new IllegalStateException("A committed order projection contained an invalid event envelope",e);}
    }

    private Outcome projectTransaction(HistoryRules.Event event,Map<String,Object> envelope,String hash,String canonicalHash,String topic,int partition,long offset){
        jdbc.query("SELECT pg_advisory_xact_lock(hashtextextended(?,0))",rs->{},event.aggregateId().toString());
        var seen=jdbc.query("SELECT payload_hash,canonical_payload_hash FROM event_inbox WHERE event_id=?",(rs,n)->new Fingerprint(rs.getString(1),rs.getString(2)),event.eventId());
        if(!seen.isEmpty()){
            if(!seen.getFirst().matches(hash,canonicalHash))throw new PoisonEventException("EVENT_ID_PAYLOAD_CONFLICT");
            jdbc.update("UPDATE event_inbox SET canonical_payload_hash=? WHERE event_id=? AND canonical_payload_hash IS NULL",canonicalHash,event.eventId());
            return Outcome.DUPLICATE;
        }
        var parked=jdbc.query("SELECT payload::text FROM pending_order_event WHERE event_id=?",(rs,n)->rs.getString(1),event.eventId());
        if(!parked.isEmpty()){if(!canonicalHash.equals(EventContent.hash(parked.getFirst())))throw new PoisonEventException("EVENT_ID_PAYLOAD_CONFLICT");return Outcome.PARKED;}
        Long current=jdbc.query("SELECT last_sequence FROM order_history_projection WHERE order_id=? FOR UPDATE",(rs,n)->rs.getLong(1),event.aggregateId()).stream().findFirst().orElse(0L);
        if(event.sequence()>current+1){
            try{jdbc.update("INSERT INTO pending_order_event(event_id,payload_hash,canonical_payload_hash,aggregate_id,aggregate_sequence,payload,source_topic,source_partition,source_offset) VALUES (?,?,?,?,?,?::jsonb,?,?,?)",event.eventId(),hash,canonicalHash,event.aggregateId(),event.sequence(),write(envelope),topic,partition,offset);}
            catch(org.springframework.dao.DuplicateKeyException e){throw new PoisonEventException("AGGREGATE_SEQUENCE_CONFLICT",e);}
            return Outcome.PARKED;
        }
        if(event.sequence()<=current)throw new PoisonEventException("STALE_EVENT_SEQUENCE");
        applyOne(event,hash,canonicalHash);
        while(true){
            long next=current+2;
            var waiting=jdbc.query("SELECT event_id,payload_hash,payload::text AS payload FROM pending_order_event WHERE aggregate_id=? AND aggregate_sequence=? FOR UPDATE",(rs,n)->new Pending((UUID)rs.getObject(1),rs.getString(2),rs.getString(3)),event.aggregateId(),next);
            if(waiting.isEmpty())break;
            Pending p=waiting.getFirst();Map<String,Object> body=read(p.payload());HistoryRules.Event nextEvent;
            try{nextEvent=HistoryRules.parse(body);}catch(RuntimeException e){throw new PoisonEventException("PARKED_EVENT_INVALID",e);}
            jdbc.update("DELETE FROM pending_order_event WHERE event_id=?",p.id());
            applyOne(nextEvent,p.hash(),EventContent.hash(p.payload()));current++;
        }
        return Outcome.APPLIED;
    }

    private void applyOne(HistoryRules.Event e,String hash,String canonicalHash){
        Instant occurred;
        try{occurred=Instant.parse(e.occurredAt());}catch(RuntimeException x){throw new PoisonEventException("INVALID_EVENT_TIME",x);}
        Map<String,Object> data=e.data();
        if(e.sequence()==1){
            if(!"OrderAccepted".equals(e.eventType()))throw new PoisonEventException("ORDER_HISTORY_MISSING_START_EVENT");
            String currency=text(data,"currency");long total=number(data,"totalMinor");Object lines=data.getOrDefault("lines",java.util.List.of());
            jdbc.update("INSERT INTO order_history_projection(order_id,customer_key,last_sequence,state,currency,total_minor,lines,occurred_at) VALUES (?,?,?, ?,?,?,?::jsonb,?)",e.aggregateId(),e.customerKey(),e.sequence(),e.state(),currency,total,write(lines),Timestamp.from(occurred));
        }else{
            int changed=jdbc.update("UPDATE order_history_projection SET last_sequence=?,state=?,occurred_at=?,updated_at=now() WHERE order_id=? AND customer_key=? AND last_sequence=?",e.sequence(),e.state(),Timestamp.from(occurred),e.aggregateId(),e.customerKey(),e.sequence()-1);
            if(changed!=1)throw new PoisonEventException("ORDER_HISTORY_SEQUENCE_OR_OWNER_CONFLICT");
        }
        try{jdbc.update("INSERT INTO event_inbox(event_id,payload_hash,canonical_payload_hash,aggregate_id,aggregate_sequence) VALUES (?,?,?,?,?)",e.eventId(),hash,canonicalHash,e.aggregateId(),e.sequence());}
        catch(org.springframework.dao.DuplicateKeyException conflict){throw new PoisonEventException("EVENT_INBOX_CONFLICT",conflict);}
        jdbc.update("INSERT INTO order_history_state_event(event_id,order_id,aggregate_sequence,event_type,state,occurred_at) VALUES (?,?,?,?,?,?)",e.eventId(),e.aggregateId(),e.sequence(),e.eventType(),e.state(),Timestamp.from(occurred));
    }

    java.util.List<Map<String,Object>> list(String customerKey){return jdbc.queryForList("SELECT order_id AS id,state,currency,total_minor AS \"totalMinor\",lines::text AS lines,occurred_at AS \"createdAt\",last_sequence AS \"lastSequence\" FROM order_history_projection WHERE customer_key=? ORDER BY occurred_at DESC LIMIT 100",customerKey).stream().map(this::decodeLines).toList();}
    OwnedGap ownedGap(String customerKey){return jdbc.queryForObject("SELECT count(*) AS count,min(received_at) AS oldest FROM pending_order_event WHERE payload->>'customerKey'=?",(rs,n)->{var oldest=rs.getTimestamp("oldest");return new OwnedGap(rs.getLong("count"),oldest==null?null:oldest.toInstant());},customerKey);}
    record OwnedGap(long count,Instant oldest) {}
    Map<String,Object> get(UUID orderId,String customerKey){var rows=jdbc.queryForList("SELECT order_id AS \"orderId\",state,currency,total_minor AS \"totalMinor\",lines::text AS lines,occurred_at AS \"updatedAt\",last_sequence AS \"lastSequence\" FROM order_history_projection WHERE order_id=? AND customer_key=?",orderId,customerKey);return rows.isEmpty()?null:decodeLines(rows.getFirst());}
    private Map<String,Object> decodeLines(Map<String,Object> row){row.put("lines",readLines((String)row.get("lines")));return row;}
    private java.util.List<?> readLines(String raw){try{return json.readValue(raw,java.util.List.class);}catch(Exception e){throw new IllegalStateException("Stored order history lines are invalid",e);}}
    Map<String,Object> status(){var counts=jdbc.queryForList("SELECT state,count(*) AS count FROM order_history_projection GROUP BY state ORDER BY state");var gaps=jdbc.queryForObject("SELECT count(*) FROM pending_order_event",Long.class);return Map.of("orders",counts,"pendingSequenceGaps",gaps==null?0:gaps,"inboxEvents",jdbc.queryForObject("SELECT count(*) FROM event_inbox",Long.class));}
    private Map<String,Object> read(String raw){try{return json.readValue(raw,Map.class);}catch(Exception e){throw new PoisonEventException("INVALID_PARKED_JSON",e);}}
    private String write(Object object){try{return json.writeValueAsString(object);}catch(Exception e){throw new IllegalArgumentException("Could not encode projection JSON",e);}}
    private static String text(Map<String,Object> data,String key){Object value=data.get(key);if(value==null)throw new PoisonEventException("MISSING_"+key.toUpperCase(java.util.Locale.ROOT));return value.toString();}
    private static long number(Map<String,Object> data,String key){Object value=data.get(key);if(!(value instanceof Number n))throw new PoisonEventException("INVALID_"+key.toUpperCase(java.util.Locale.ROOT));return n.longValue();}
    private static String sha256(String value){try{return java.util.HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8)));}catch(Exception e){throw new IllegalStateException(e);}}
    enum Outcome{APPLIED,DUPLICATE,PARKED}
    record Fingerprint(String raw,String canonical){boolean matches(String incomingRaw,String incomingCanonical){return canonical==null?raw.equals(incomingRaw):canonical.equals(incomingCanonical);}}
    record Pending(UUID id,String hash,String payload){}
    static class PoisonEventException extends RuntimeException{private final String code;PoisonEventException(String code){super(code);this.code=code;}PoisonEventException(String code,Throwable cause){super(code,cause);this.code=code;}String code(){return code;}}
}
