package com.supersports.orders;

import static org.junit.jupiter.api.Assertions.*;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class ReturnRefundAllocationTest {
    private static final UUID A=UUID.fromString("00000000-0000-4000-8000-000000000001");
    private static final UUID B=UUID.fromString("00000000-0000-4000-8000-000000000002");
    @Test void allocatesTaxAndUnitRemaindersDeterministically(){
        var units=ReturnRefundAllocation.allocate(List.of(new ReturnRefundAllocation.Line(B,2,5),new ReturnRefundAllocation.Line(A,2,5)),3,Map.of(),Map.of(A,2,B,2));
        assertEquals(13,units.stream().mapToLong(ReturnRefundAllocation.Unit::refundMinor).sum());
        assertEquals(List.of(A,A,B,B),units.stream().map(ReturnRefundAllocation.Unit::skuId).toList());
        assertEquals(List.of(4L,3L,4L,2L),units.stream().map(ReturnRefundAllocation.Unit::refundMinor).toList());
    }
    @Test void priorReturnUnitsAreNotClaimedAgainAndQuantityCannotExceedOrder(){
        var units=ReturnRefundAllocation.allocate(List.of(new ReturnRefundAllocation.Line(A,3,10)),0,Map.of(A,1),Map.of(A,2));
        assertEquals(List.of(1,2),units.stream().map(ReturnRefundAllocation.Unit::ordinal).toList());
        assertThrows(IllegalArgumentException.class,()->ReturnRefundAllocation.allocate(List.of(new ReturnRefundAllocation.Line(A,3,10)),0,Map.of(A,2),Map.of(A,2)));
    }
}
