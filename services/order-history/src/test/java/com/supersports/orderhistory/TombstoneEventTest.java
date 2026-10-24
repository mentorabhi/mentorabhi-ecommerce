package com.supersports.orderhistory;

import static org.junit.jupiter.api.Assertions.*;
import org.junit.jupiter.api.Test;

class TombstoneEventTest {
    @Test void tombstoneIsQuarantinedAndHasAFingerprintDistinctFromStringValues(){
        var index=new ProjectionEventIndex();
        index.add("commerce.order.events.v1:0:7",null);
        assertTrue(index.events().isEmpty());
        assertEquals(1,index.poison().size());
        assertEquals("commerce.order.events.v1:0:7",index.poison().getFirst().get("coordinate"));
        assertEquals(EventContent.rawHash(null),index.poison().getFirst().get("rawHash"));
        assertNotEquals(EventContent.rawHash(""),EventContent.rawHash(null));
        assertNotEquals(EventContent.rawHash("null"),EventContent.rawHash(null));
        assertNotEquals(EventContent.rawHash("\ufffd"),EventContent.rawHash(null));
    }
}
