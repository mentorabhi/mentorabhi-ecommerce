package com.supersports.orderhistory;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import java.util.Map;
import org.junit.jupiter.api.Test;

class HistoryRulesTest {
    private Map<String,Object> envelope(String type,long sequence){return Map.of("eventId","00000000-0000-4000-8000-000000000001","eventType",type,"eventVersion",1,"aggregateType","Order","aggregateId","00000000-0000-4000-8000-000000000002","aggregateSequence",sequence,"occurredAt","2026-10-24T00:00:00Z","customerKey","a".repeat(64),"data",Map.of());}
    @Test void supportedEventsMapToOrderStatesAndPreserveOwner(){
        assertThat(HistoryRules.parse(envelope("OrderAccepted",1)).state()).isEqualTo("PENDING_PAYMENT");
        assertThat(HistoryRules.parse(envelope("OrderConfirmed",2)).state()).isEqualTo("CONFIRMED");
        assertThat(HistoryRules.parse(envelope("FulfillmentScheduled",3)).state()).isEqualTo("FULFILLMENT_SCHEDULED");
        assertThat(HistoryRules.parse(envelope("OrderCheckoutExpired",4)).customerKey()).isEqualTo("a".repeat(64));
    }
    @Test void rejectsUnknownTypesBadSequenceAndWrongAggregate(){
        assertThatThrownBy(()->HistoryRules.parse(envelope("Unknown",1))).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(()->HistoryRules.parse(envelope("OrderAccepted",0))).isInstanceOf(IllegalArgumentException.class);
        var wrong=new java.util.HashMap<>(envelope("OrderAccepted",1));wrong.put("aggregateType","Cart");
        assertThatThrownBy(()->HistoryRules.parse(wrong)).isInstanceOf(IllegalArgumentException.class);
    }
}
