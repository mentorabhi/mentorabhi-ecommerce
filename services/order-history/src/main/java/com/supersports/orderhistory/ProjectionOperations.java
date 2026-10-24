package com.supersports.orderhistory;

import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

@Component
class ProjectionOperations {
    private final JdbcTemplate jdbc;
    private final OperatorKafka kafka;
    private final HistoryProjector projector;
    private final String topic,dlq,group;
    private final boolean rebuildTarget;
    ProjectionOperations(JdbcTemplate jdbc,OperatorKafka kafka,HistoryProjector projector,
                         @Value("${order-history.topic}")String topic,@Value("${order-history.dlq-topic}")String dlq,
                         @Value("${order-history.consumer-group}")String group,@Value("${order-history.rebuild-target:false}")boolean rebuildTarget){
        this.jdbc=jdbc;this.kafka=kafka;this.projector=projector;this.topic=topic;this.dlq=dlq;this.group=group;this.rebuildTarget=rebuildTarget;
    }

    Map<String,Object> snapshot(){
        var events=rows("SELECT row_to_json(r)::text FROM (SELECT event_id AS \"eventId\",payload_hash AS \"rawHash\",canonical_payload_hash AS \"canonicalHash\" FROM event_inbox ORDER BY event_id) r");
        var orders=rows("SELECT row_to_json(r)::text FROM (SELECT order_id AS \"orderId\",state,currency,total_minor AS \"totalMinor\",customer_key AS \"customerKey\",last_sequence AS \"lastSequence\",lines FROM order_history_projection ORDER BY order_id) r");
        var timeline=rows("SELECT row_to_json(r)::text FROM (SELECT event_id AS \"eventId\",order_id AS \"orderId\",aggregate_sequence AS sequence,event_type AS \"eventType\",state,occurred_at AS \"occurredAt\" FROM order_history_state_event ORDER BY event_id) r");
        var audit=rows("SELECT row_to_json(r)::text FROM (SELECT * FROM order_history_replay_audit ORDER BY operation_id) r");
        var deliveries=rows("SELECT row_to_json(r)::text FROM (SELECT operation_id,source_partition,record_key,published_topic,published_partition,published_offset,published_at,encode(sha256(convert_to(corrected_payload,'UTF8')),'hex') AS payload_hash FROM order_history_replay_delivery ORDER BY operation_id) r");
        return Map.of("database",jdbc.queryForObject("SELECT current_database()",String.class),"events",events,"orders",orders,"timeline",timeline,
                      "pendingEvents",jdbc.queryForObject("SELECT count(*) FROM pending_order_event",Long.class),"audit",audit,"deliveries",deliveries);
    }

    Map<String,Object> inspect(){
        var index=new ProjectionEventIndex();
        var highWater=kafka.scan(topic,record->index.add(coordinate(record),record.value()));
        includeDlq(index);
        return Map.of("snapshot",snapshot(),"scan",scan(index,highWater));
    }

    Map<String,Object> rebuild(boolean injectMismatch){
        String database=jdbc.queryForObject("SELECT current_database()",String.class);
        if(!rebuildTarget || database==null || !database.matches("order_history_r_[a-f0-9]{12}") || !group.equals("order-history-r-"+database.substring("order_history_r_".length())))throw new IllegalArgumentException("REBUILD_REQUIRES_ISOLATED_TARGET");
        var index=new ProjectionEventIndex();
        var marks=kafka.rebuild(topic,group,record->{
            String coordinate=coordinate(record);index.add(coordinate,record.value());
            try{projector.project(record.value(),record.topic(),record.partition(),record.offset());}
            catch(HistoryProjector.PoisonEventException poison){index.quarantine(coordinate,poison.code(),EventContent.rawHash(record.value()));}
        });
        includeDlq(index);
        if(injectMismatch){int changed=jdbc.update("UPDATE order_history_projection SET total_minor=total_minor+1 WHERE order_id=(SELECT order_id FROM order_history_projection ORDER BY order_id LIMIT 1)");if(changed!=1)throw new IllegalArgumentException("MISMATCH_INJECTION_REQUIRES_ORDER");}
        return Map.of("snapshot",snapshot(),"scan",scan(index,(Map<String,Long>)marks.get("secondHighWater")),"watermarks",marks);
    }

    private void includeDlq(ProjectionEventIndex index){
        kafka.scan(dlq,record->{
            var header=record.headers().lastHeader("error-code");
            String code=header==null?"POISON_EVENT":new String(header.value(),StandardCharsets.UTF_8);
            index.quarantine(record.key(),code,EventContent.rawHash(record.value()));
        });
    }
    private Map<String,Object> scan(ProjectionEventIndex index,Map<String,Long> marks){return Map.of("events",index.events(),"poison",index.poison(),"conflicts",index.conflicts(),"highWater",marks);}
    private String coordinate(org.apache.kafka.clients.consumer.ConsumerRecord<String,String> record){return record.topic()+":"+record.partition()+":"+record.offset();}
    private List<Map<String,Object>> rows(String query){return jdbc.query(query,(rs,n)->EventContent.read(rs.getString(1)));}
}
