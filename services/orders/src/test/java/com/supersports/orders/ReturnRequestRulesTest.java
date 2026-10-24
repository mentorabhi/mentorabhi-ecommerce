package com.supersports.orders;

import static org.junit.jupiter.api.Assertions.*;
import java.time.Instant;
import java.util.List;
import org.junit.jupiter.api.Test;

class ReturnRequestRulesTest {
    @Test void normalizesOrderIndependentPayloadForIdempotency(){
        var first=ReturnRequestRules.normalize(List.of(new ReturnRequestRules.LineInput("00000000-0000-4000-8000-000000000002",1),new ReturnRequestRules.LineInput("00000000-0000-4000-8000-000000000001",2)));
        var second=ReturnRequestRules.normalize(List.of(new ReturnRequestRules.LineInput("00000000-0000-4000-8000-000000000001",2),new ReturnRequestRules.LineInput("00000000-0000-4000-8000-000000000002",1)));
        assertEquals(ReturnRequestRules.payloadHash(first),ReturnRequestRules.payloadHash(second));
    }
    @Test void rejectsDuplicateOrInvalidReturnLines(){
        var sku="00000000-0000-4000-8000-000000000001";
        assertThrows(IllegalArgumentException.class,()->ReturnRequestRules.normalize(List.of(new ReturnRequestRules.LineInput(sku,1),new ReturnRequestRules.LineInput(sku,2))));
        assertThrows(IllegalArgumentException.class,()->ReturnRequestRules.normalize(List.of(new ReturnRequestRules.LineInput(sku,0))));
    }
    @Test void enforcesReturnDeadlineInclusively(){
        Instant delivered=Instant.parse("2026-01-01T00:00:00Z");
        assertTrue(ReturnRequestRules.withinWindow(delivered,delivered.plusSeconds(30L*86400),30));
        assertFalse(ReturnRequestRules.withinWindow(delivered,delivered.plusSeconds(30L*86400+1),30));
    }
}
