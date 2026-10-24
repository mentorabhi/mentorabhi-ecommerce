package com.supersports.orderhistory;

import java.time.Duration;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;
import jakarta.annotation.PreDestroy;
import org.apache.kafka.clients.admin.AdminClient;
import org.apache.kafka.clients.admin.OffsetSpec;
import org.apache.kafka.common.TopicPartition;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
@ConditionalOnProperty(name="order-history.operator-mode",havingValue="false",matchIfMissing=true)
class ProjectionFreshness {
    private final AdminClient admin;
    private final String topic,group;
    private final Duration staleAfter,gapTimeout;
    private volatile Observation observation=new Observation(null,false,0);
    private volatile Instant lastConsumerPoll;

    ProjectionFreshness(@Value("${spring.kafka.bootstrap-servers}")String brokers,@Value("${order-history.topic}")String topic,
                        @Value("${order-history.consumer-group}")String group,@Value("${order-history.stale-after-seconds:10}")long stale,
                        @Value("${order-history.gap-timeout-seconds:30}")long gap){
        this.topic=topic;this.group=group;this.staleAfter=Duration.ofSeconds(stale);this.gapTimeout=Duration.ofSeconds(gap);
        Properties properties=new Properties();properties.put("bootstrap.servers",brokers);
        properties.put("request.timeout.ms","2000");properties.put("default.api.timeout.ms","3000");
        admin=AdminClient.create(properties);
    }

    void polled(){lastConsumerPoll=Instant.now();}

    @Scheduled(fixedDelayString="${order-history.probe-interval-ms:3000}")
    void probe(){
        try{
            var description=admin.describeTopics(List.of(topic)).allTopicNames().get(2,TimeUnit.SECONDS).get(topic);
            var requests=description.partitions().stream().collect(Collectors.toMap(partition->new TopicPartition(topic,partition.partition()),partition->OffsetSpec.latest()));
            var ends=admin.listOffsets(requests).all().get(2,TimeUnit.SECONDS);
            var committed=admin.listConsumerGroupOffsets(group).partitionsToOffsetAndMetadata().get(2,TimeUnit.SECONDS);
            long lag=ends.entrySet().stream().mapToLong(entry->{var offset=committed.get(entry.getKey());return Math.max(0,entry.getValue().offset()-(offset==null?0:offset.offset()));}).sum();
            observation=new Observation(Instant.now(),true,lag);
        }catch(Exception failure){observation=new Observation(Instant.now(),false,0);}
    }

    Map<String,Object> view(HistoryProjector.OwnedGap gap){
        Observation observed=observation;
        String state=FreshnessRules.state(Instant.now(),observed.at(),observed.reachable(),lastConsumerPoll,observed.lag(),gap.count(),gap.oldest(),staleAfter,gapTimeout);
        Map<String,Object> result=new LinkedHashMap<>();result.put("state",state);
        result.put("checkedAt",observed.at()==null?null:observed.at().toString());
        result.put("pendingOwnEvents",gap.count());result.put("gapSince",gap.oldest()==null?null:gap.oldest().toString());
        return result;
    }
    @PreDestroy void close(){admin.close(Duration.ofSeconds(2));}
    record Observation(Instant at,boolean reachable,long lag) {}
}
