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
        Properties properties = new Properties();
        properties.put("bootstrap.servers", brokers);
        properties.put("group.id", "order-history-operator-" + UUID.randomUUID());
        properties.put("key.deserializer", "org.apache.kafka.common.serialization.StringDeserializer");
        properties.put("value.deserializer", "org.apache.kafka.common.serialization.StringDeserializer");
        properties.put("enable.auto.commit", "false");
        properties.put("isolation.level", "read_committed");
        properties.put("default.api.timeout.ms", "30000");
        try (var consumer = new KafkaConsumer<String,String>(properties)) {
            List<TopicPartition> partitions = consumer.partitionsFor(topic).stream().map(p -> new TopicPartition(topic,p.partition())).toList();
            consumer.assign(partitions);
            consumer.seekToBeginning(partitions);
            var marks = consumer.endOffsets(partitions);
            long deadline = System.nanoTime() + Duration.ofSeconds(90).toNanos();
            while (partitions.stream().anyMatch(p -> consumer.position(p) < marks.get(p))) {
                if (System.nanoTime() >= deadline) throw new IllegalStateException("KAFKA_SCAN_TIMEOUT");
                for (var record : consumer.poll(Duration.ofMillis(300))) {
                    if (record.offset() < marks.get(new TopicPartition(record.topic(),record.partition()))) action.accept(record);
                }
            }
            return marks.entrySet().stream().collect(Collectors.toMap(e -> Integer.toString(e.getKey().partition()), Map.Entry::getValue));
        }
    }

    RecordMetadata publish(String topic, int partition, String key, String payload) {
        Properties properties = new Properties();
        properties.put("bootstrap.servers", brokers);
        properties.put("key.serializer", "org.apache.kafka.common.serialization.StringSerializer");
        properties.put("value.serializer", "org.apache.kafka.common.serialization.StringSerializer");
        properties.put("enable.idempotence", "true");
        properties.put("acks", "all");
        properties.put("delivery.timeout.ms", "30000");
        properties.put("request.timeout.ms", "10000");
        properties.put("max.block.ms", "15000");
        try (var producer = new KafkaProducer<String,String>(properties)) {
            return producer.send(new ProducerRecord<>(topic,partition,key,payload)).get(35,java.util.concurrent.TimeUnit.SECONDS);
        } catch (Exception error) { throw new IllegalStateException("KAFKA_PUBLICATION_FAILED"); }
    }
}
