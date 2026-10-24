package com.supersports.orderhistory;

import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.UUID;
import java.util.function.Consumer;
import java.util.stream.Collectors;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.clients.consumer.OffsetAndMetadata;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.clients.producer.RecordMetadata;
import org.apache.kafka.common.TopicPartition;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
class OperatorKafka {
    private final String brokers;
    OperatorKafka(@Value("${spring.kafka.bootstrap-servers}") String brokers) { this.brokers = brokers; }

    Map<String,Long> scan(String topic, Consumer<ConsumerRecord<String,String>> action) {
        try(var consumer=new KafkaConsumer<String,String>(consumerProperties("order-history-operator-"+UUID.randomUUID()))) {
            var partitions=partitions(consumer,topic);
            consumer.assign(partitions);consumer.seekToBeginning(partitions);
            var marks=consumer.endOffsets(partitions);readTo(consumer,marks,action);
            return printable(marks);
        }
    }

    Map<String,Object> rebuild(String topic,String group,Consumer<ConsumerRecord<String,String>> action) {
        if(!group.matches("order-history-r-[a-f0-9]{12}"))throw new IllegalArgumentException("INVALID_REBUILD_GROUP");
        try(var consumer=new KafkaConsumer<String,String>(consumerProperties(group))) {
            var partitions=partitions(consumer,topic);consumer.assign(partitions);
            if(consumer.beginningOffsets(partitions).values().stream().anyMatch(offset->offset!=0))throw new IllegalStateException("RETAINED_HISTORY_START_MISSING");
            consumer.seekToBeginning(partitions);
            var first=consumer.endOffsets(partitions);readTo(consumer,first,action);
            first.forEach(consumer::seek);
            var second=consumer.endOffsets(partitions);readTo(consumer,second,action);
            consumer.commitSync(second.entrySet().stream().collect(Collectors.toMap(Map.Entry::getKey,e->new OffsetAndMetadata(e.getValue()))));
            return Map.of("firstHighWater",printable(first),"secondHighWater",printable(second));
        }
    }

    private Properties consumerProperties(String group) {
        Properties properties=new Properties();
        properties.put("bootstrap.servers",brokers);
        properties.put("group.id",group);
        properties.put("key.deserializer","org.apache.kafka.common.serialization.StringDeserializer");
        properties.put("value.deserializer","org.apache.kafka.common.serialization.StringDeserializer");
        properties.put("enable.auto.commit","false");
        properties.put("isolation.level","read_committed");
        properties.put("default.api.timeout.ms","30000");
        return properties;
    }

    private List<TopicPartition> partitions(KafkaConsumer<String,String> consumer,String topic){
        return consumer.partitionsFor(topic).stream().map(p->new TopicPartition(topic,p.partition())).toList();
    }

    private void readTo(KafkaConsumer<String,String> consumer,Map<TopicPartition,Long> marks,Consumer<ConsumerRecord<String,String>> action){
        long deadline=System.nanoTime()+Duration.ofSeconds(90).toNanos();
        while(marks.keySet().stream().anyMatch(p->consumer.position(p)<marks.get(p))) {
            if(System.nanoTime()>=deadline)throw new IllegalStateException("KAFKA_SCAN_TIMEOUT");
            for(var record:consumer.poll(Duration.ofMillis(300))) {
                if(record.offset()<marks.get(new TopicPartition(record.topic(),record.partition())))action.accept(record);
            }
        }
    }

    private Map<String,Long> printable(Map<TopicPartition,Long> marks){
        return marks.entrySet().stream().collect(Collectors.toMap(e->Integer.toString(e.getKey().partition()),Map.Entry::getValue));
    }

    RecordMetadata publish(String topic,int partition,String key,String payload) {
        Properties properties=new Properties();
        properties.put("bootstrap.servers",brokers);
        properties.put("key.serializer","org.apache.kafka.common.serialization.StringSerializer");
        properties.put("value.serializer","org.apache.kafka.common.serialization.StringSerializer");
        properties.put("enable.idempotence","true");
        properties.put("acks","all");
        properties.put("delivery.timeout.ms","30000");
        properties.put("request.timeout.ms","10000");
        properties.put("max.block.ms","15000");
        try(var producer=new KafkaProducer<String,String>(properties)) {
            return producer.send(new ProducerRecord<>(topic,partition,key,payload)).get(35,java.util.concurrent.TimeUnit.SECONDS);
        } catch(Exception error){throw new IllegalStateException("KAFKA_PUBLICATION_FAILED");}
    }
}
