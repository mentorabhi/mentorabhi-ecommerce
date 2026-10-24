package com.supersports.orders;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;

class OutboxEventWriterTest {
    @Test void legacyEventIdIsDeterministicAndUsesUuidV5(){
        var first=OutboxEventWriter.legacyEventId(123456L);
        assertThat(first).isEqualTo(OutboxEventWriter.legacyEventId(123456L));
        assertThat(first.version()).isEqualTo(5);
        assertThat(first).isNotEqualTo(OutboxEventWriter.legacyEventId(123457L));
    }

    @Test void newEventsUseAllocatedSequenceAndPersistEightParameters(){
        JdbcTemplate jdbc=mock(JdbcTemplate.class);UUID order=UUID.randomUUID();
        when(jdbc.queryForObject(anyString(),eq(Long.class),eq(order))).thenReturn(1L);
        OutboxEventWriter writer=new OutboxEventWriter(jdbc,"an-owner-key-longer-than-thirty-two-characters");
        assertThatThrownBy(()->writer.append(order,"customer","OrderAccepted",Map.of("state","PENDING_PAYMENT")))
                .isInstanceOf(IllegalStateException.class);
        writer.enableAfterBackfill();
        writer.append(order,"customer","OrderAccepted",Map.of("state","PENDING_PAYMENT"));
        var parameters=org.mockito.ArgumentCaptor.forClass(Object[].class);
        verify(jdbc).update(org.mockito.ArgumentMatchers.contains("INSERT INTO order_outbox"),parameters.capture());
        assertThat(parameters.getValue()).hasSize(8);
        assertThat(parameters.getValue()[7]).isInstanceOf(java.sql.Timestamp.class);
        assertThat(parameters.getValue()[2].toString()).contains("\"aggregateSequence\":1");
    }

    @Test void postPurchaseWriterAllowsOnlyReviewedV2Types(){
        JdbcTemplate jdbc=mock(JdbcTemplate.class);UUID order=UUID.randomUUID();
        when(jdbc.queryForObject(anyString(),eq(Long.class),eq(order))).thenReturn(2L);
        OutboxEventWriter writer=new OutboxEventWriter(jdbc,"an-owner-key-longer-than-thirty-two-characters");writer.enableAfterBackfill();
        var data=Map.<String,Object>of("orderId",order.toString(),"state","CANCELLED","operationId",UUID.randomUUID().toString(),"refundMinor",100,"currency","INR","reasonCode","CUSTOMER_REQUEST");
        writer.appendPostPurchase(order,"customer","OrderCancelled",data);
        var parameters=org.mockito.ArgumentCaptor.forClass(Object[].class);
        verify(jdbc).update(org.mockito.ArgumentMatchers.contains("INSERT INTO order_outbox"),parameters.capture());
        assertThat(parameters.getValue()[4]).isEqualTo(2);
        assertThat(parameters.getValue()[2].toString()).contains("\"eventVersion\":2","\"eventType\":\"OrderCancelled\"");
        assertThatThrownBy(()->writer.appendPostPurchase(order,"customer","ArbitraryEvent",data)).isInstanceOf(IllegalArgumentException.class);
    }
}
