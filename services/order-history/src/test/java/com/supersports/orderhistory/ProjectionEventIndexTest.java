package com.supersports.orderhistory;

import static org.junit.jupiter.api.Assertions.*;
import java.util.Map;
import org.junit.jupiter.api.Test;

class ProjectionEventIndexTest {
    private String event(String time){return EventContent.write(Map.of("eventId","00000000-0000-4000-8000-000000000001","eventType","OrderConfirmed","eventVersion",1,"aggregateType","Order","aggregateId","00000000-0000-4000-8000-000000000002","aggregateSequence",2,"occurredAt",time,"customerKey","a".repeat(64),"data",Map.of("orderId","00000000-0000-4000-8000-000000000002","state","CONFIRMED")));}

    @Test void duplicateRecordsKeepOneEventWhileConflictingContentIsVisible(){
        var index=new ProjectionEventIndex();
        String original=event("2026-10-24T00:00:00Z");
        index.add("topic:0:0",original);index.add("topic:0:1",original);
        assertEquals(1,index.events().size());assertTrue(index.conflicts().isEmpty());
        index.add("topic:0:2",event("2026-10-24T00:00:01Z"));
        assertFalse(index.conflicts().isEmpty());
        index.quarantine("topic:0:2","CONFLICT",EventContent.rawHash(event("2026-10-24T00:00:01Z")));
        assertTrue(index.conflicts().isEmpty());assertEquals(1,index.poison().size());
    }

    @Test void malformedRecordsAreQuarantinedAndDlqContentMustMatchSource(){
        var index=new ProjectionEventIndex();index.add("topic:0:0","not-json");
        assertEquals(0,index.events().size());assertEquals(1,index.poison().size());
        index.quarantine("topic:0:0","INVALID_JSON","wrong-source-hash");
        assertFalse(index.conflicts().isEmpty());
    }
}
