package com.supersports.orderhistory;

import static org.junit.jupiter.api.Assertions.*;
import java.time.Duration;
import java.time.Instant;
import org.junit.jupiter.api.Test;

class FreshnessRulesTest {
    private final Instant now=Instant.parse("2026-10-24T12:00:00Z");
    private String state(Instant checked,boolean reachable,Instant polled,long lag,long gaps,Instant oldest){
        return FreshnessRules.state(now,checked,reachable,polled,lag,gaps,oldest,Duration.ofSeconds(10),Duration.ofSeconds(30));
    }
    @Test void idleButConnectedAndCaughtUpIsCurrent(){assertEquals("CURRENT",state(now,true,now,0,0,null));}
    @Test void unavailableBrokerStaleObservationOrDeadConsumerIsExplicit(){
        assertEquals("UNAVAILABLE",state(now,false,now,0,0,null));
        assertEquals("UNAVAILABLE",state(now.minusSeconds(11),true,now,0,0,null));
        assertEquals("UNAVAILABLE",state(now,true,now.minusSeconds(11),0,0,null));
        assertEquals("UNAVAILABLE",state(null,false,null,0,0,null));
    }
    @Test void backlogAndYoungOwnedGapAreDelayed(){
        assertEquals("DELAYED",state(now,true,now,1,0,null));
        assertEquals("DELAYED",state(now,true,now,0,1,now.minusSeconds(5)));
    }
    @Test void timedOwnedGapIsBlockedButAnUnrelatedOwnerRemainsCurrent(){
        assertEquals("BLOCKED",state(now,true,now,0,1,now.minusSeconds(31)));
        assertEquals("CURRENT",state(now,true,now,0,0,null));
        assertEquals("UNAVAILABLE",state(now,false,now,0,1,now.minusSeconds(31)));
    }
}
