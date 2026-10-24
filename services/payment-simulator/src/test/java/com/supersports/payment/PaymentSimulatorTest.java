package com.supersports.payment;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;

class PaymentSimulatorTest {
    @Test void rejectsInvalidMoneyBeforeWriting(){
        JdbcTemplate jdbc=mock(JdbcTemplate.class);var simulator=new PaymentSimulator(jdbc);
        assertThrows(IllegalArgumentException.class,()->simulator.execute(UUID.randomUUID(),"AUTHORIZE","key",1,-1,"INR","APPROVE"));
        verifyNoInteractions(jdbc);
    }
    @Test void authorizationIsDeterministicAndRecorded(){
        JdbcTemplate jdbc=mock(JdbcTemplate.class);UUID id=UUID.randomUUID();
        when(jdbc.queryForObject(anyString(),eq(Long.class),eq(id))).thenReturn(7L);
        when(jdbc.queryForList(contains("operation_key=?"),eq("order:authorize"))).thenReturn(List.of());
        when(jdbc.queryForList(contains("WHERE order_id=? ORDER BY id"),eq(id))).thenReturn(List.of());
        when(jdbc.update(contains("INSERT INTO payment_operation"),any(Object[].class))).thenReturn(1);
        var result=new PaymentSimulator(jdbc).execute(id,"AUTHORIZE","order:authorize",7,1234,"INR","APPROVE");
        assertEquals("AUTHORIZED",result.get("state"));assertEquals(false,result.get("replayed"));
        verify(jdbc).update(contains("INSERT INTO payment_operation"),eq(id),eq("AUTHORIZE"),eq("order:authorize"),eq("AUTHORIZE:1234:INR:APPROVE"),eq(1234L),eq("INR"),eq("AUTHORIZED"),eq(7L));
    }
    @Test void identicalOperationKeyRetryReturnsOriginalReceipt(){
        JdbcTemplate jdbc=mock(JdbcTemplate.class);UUID id=UUID.randomUUID();
        when(jdbc.queryForObject(anyString(),eq(Long.class),eq(id))).thenReturn(3L);
        when(jdbc.queryForList(contains("operation_key=?"),eq("same-key"))).thenReturn(List.of(Map.of("order_id",id,"payload_hash","AUTHORIZE:100:INR:APPROVE","state","AUTHORIZED")));
        var result=new PaymentSimulator(jdbc).execute(id,"AUTHORIZE","same-key",3,100,"INR","APPROVE");
        assertEquals("AUTHORIZED",result.get("state"));assertEquals(true,result.get("replayed"));
        verify(jdbc,never()).update(contains("INSERT INTO payment_operation"),any(Object[].class));
    }
    @Test void sameKeyCannotReplayAcrossOrderOwnership(){
        JdbcTemplate jdbc=mock(JdbcTemplate.class);UUID id=UUID.randomUUID();
        when(jdbc.queryForObject(anyString(),eq(Long.class),eq(id))).thenReturn(3L);
        when(jdbc.queryForList(contains("operation_key=?"),eq("same-key"))).thenReturn(List.of(Map.of("order_id",UUID.randomUUID(),"payload_hash","AUTHORIZE:100:INR:APPROVE","state","AUTHORIZED")));
        assertThrows(PaymentSimulator.OperationConflictException.class,()->new PaymentSimulator(jdbc).execute(id,"AUTHORIZE","same-key",3,100,"INR","APPROVE"));
    }
    @Test void staleFenceDoesNotReadOrWriteAnOperation(){
        JdbcTemplate jdbc=mock(JdbcTemplate.class);UUID id=UUID.randomUUID();
        when(jdbc.queryForObject(anyString(),eq(Long.class),eq(id))).thenReturn(5L);
        assertThrows(PaymentSimulator.StaleFenceException.class,()->new PaymentSimulator(jdbc).execute(id,"AUTHORIZE","key",4,10,"INR","APPROVE"));
    }
}
