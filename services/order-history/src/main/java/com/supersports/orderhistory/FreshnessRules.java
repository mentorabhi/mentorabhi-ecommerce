package com.supersports.orderhistory;

import java.time.Duration;
import java.time.Instant;

final class FreshnessRules {
    private FreshnessRules() {}
    static String state(Instant now,Instant checked,boolean reachable,Instant polled,long lag,long ownGaps,
                        Instant oldestGap,Duration staleAfter,Duration gapTimeout){
        if(!reachable || checked==null || polled==null || Duration.between(checked,now).compareTo(staleAfter)>0
                || Duration.between(polled,now).compareTo(staleAfter)>0)return "UNAVAILABLE";
        if(ownGaps>0 && oldestGap!=null && Duration.between(oldestGap,now).compareTo(gapTimeout)>=0)return "BLOCKED";
        if(lag>0 || ownGaps>0)return "DELAYED";
        return "CURRENT";
    }
}
