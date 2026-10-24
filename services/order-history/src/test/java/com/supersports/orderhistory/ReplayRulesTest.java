package com.supersports.orderhistory;

import static org.junit.jupiter.api.Assertions.*;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class ReplayRulesTest {
    private static final String ID="00000000-0000-0000-0000-000000000001";
    private static final String ORDER="00000000-0000-0000-0000-000000000002";
    private Map<String,Object> event(){return new LinkedHashMap<>(Map.of("eventId",ID,"aggregateId",ORDER,"aggregateType","Order","aggregateSequence",2,"eventType","OrderConfirmed","eventVersion",1,"occurredAt","2026-10-24T00:00:00Z","customerKey","a".repeat(64),"data",Map.of("orderId",ORDER,"state","CONFIRMED")));}

    @Test void canonicalHashIgnoresObjectFormattingButPreservesArrayOrder(){
        assertEquals(EventContent.hash("{\"b\":2,\"a\":{\"y\":1,\"x\":[1,2]}}"),EventContent.hash("{ \"a\": {\"x\":[1,2],\"y\":1}, \"b\":2 }"));
        assertNotEquals(EventContent.hash("{\"a\":[1,2]}"),EventContent.hash("{\"a\":[2,1]}"));
        assertEquals(EventContent.hash("{\"a\":1}"),EventContent.hash("{\"a\":1.0}"));
    }

    @Test void correctionCanFixVersionWithoutChangingIdentity(){
        var original=event();original.put("eventVersion",999);
        assertEquals(ID,ReplayRules.correction(EventContent.write(original),EventContent.write(event())).eventId().toString());
        for(String key:List.of("eventId","aggregateId","aggregateSequence","customerKey")){
            var changed=event();changed.put(key,key.equals("aggregateSequence")?3:ID);
            if(changed.get(key).equals(event().get(key)))changed.put(key,ORDER);
            assertThrows(IllegalArgumentException.class,()->ReplayRules.correction(EventContent.write(original),EventContent.write(changed)),key);
        }
    }

    @Test void sourceCoordinateAcceptsOnlyTheOrdersTopicAndNonnegativeCoordinates(){
        var coordinate=ReplayRules.coordinate("commerce.order.events.v1:2:42","commerce.order.events.v1");
        assertEquals(2,coordinate.partition());assertEquals(42,coordinate.offset());
        for(String invalid:List.of("other:0:1","commerce.order.events.v1:-1:1","commerce.order.events.v1:0:-1","commerce.order.events.v1:99999999999999:1","commerce.order.events.v1:0:1:2"))
            assertThrows(IllegalArgumentException.class,()->ReplayRules.coordinate(invalid,"commerce.order.events.v1"));
    }

    @Test void legacyHashesRequireOriginalBytesUntilCanonicalEvidenceIsAvailable(){
        var legacy=new HistoryProjector.Fingerprint("original-bytes",null);
        assertTrue(legacy.matches("original-bytes","canonical"));
        assertFalse(legacy.matches("reformatted-bytes","canonical"));
        var canonical=new HistoryProjector.Fingerprint("original-bytes","canonical");
        assertTrue(canonical.matches("reformatted-bytes","canonical"));
        assertFalse(canonical.matches("original-bytes","changed-content"));
    }
}
