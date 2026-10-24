package com.supersports.payment;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;

class PaymentSimulatorTest {
    @Test void rejectsInvalidMoneyBeforeWriting() {
        JdbcTemplate jdbc=mock(JdbcTemplate.class);PaymentSimulator simulator=new PaymentSimulator(jdbc);
        assertThrows(IllegalArgumentException.class,()->simulator.execute(UUID.randomUUID(),"AUTHORIZE","key",1,-1,"INR","APPROVE"));
        verifyNoInteractions(jdbc);
    }
    @Test void authorizationIsDeterministicAndRecorded() {
        JdbcTemplate jdbc=mock(JdbcTemplate.class);UUID id=UUID.randomUUID();
        when(jdbc.queryForObject(anyString(),eq(Long.class),eq(id))).thenReturn(7L);
        when(jdbc.queryForList(anyString(),any(Object[].class))).thenReturn(List.of());
        PaymentSimulator simulator=new PaymentSimulator(jdbc);
        var result=simulator.execute(id,"AUTHORIZE","order:authorize",7,1234,"INR","APPROVE");
        assertEquals("AUTHORIZED",result.get("state"));assertEquals(false,result.get("replayed"));
        verify(jdbc).update(contains("INSERT INTO payment_operation"),eq(id),eq("AUTHORIZE"),eq("order:authorize"),eq("AUTHORIZE:1234:INR:APPROVE"),eq(1234L),eq("INR"),eq("AUTHORIZED"),eq(7L));
    }
    @Test void declineModeCannotAuthorize() {
        JdbcTemplate jdbc=mock(JdbcTemplate.class);UUID id=UUID.randomUUID();
        when(jdbc.queryForObject(anyString(),eq(Long.class),eq(id))).thenReturn(3L);
        when(jdbc.queryForList(anyString(),any(Object[].class))).thenReturn(List.of());
        var result=new PaymentSimulator(jdbc).execute(id,"AUTHORIZE","order:authorize",3,1234,"INR","DECLINE");
        assertEquals("DECLINED",result.get("state"));
    }
    @Test void rejectsStaleFence() {
        JdbcTemplate jdbc=mock(JdbcTemplate.class);UUID id=UUID.randomUUID();
        when(jdbc.queryForObject(anyString(),eq(Long.class),eq(id))).thenReturn(5L);
        assertThrows(PaymentSimulator.StaleFenceException.class,()->new PaymentSimulator(jdbc).execute(id,"AUTHORIZE","key",4,10,"INR","APPROVE"));
    }
}
