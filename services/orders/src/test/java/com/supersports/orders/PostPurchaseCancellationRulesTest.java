package com.supersports.orders;

import static org.junit.jupiter.api.Assertions.*;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class PostPurchaseCancellationRulesTest {
    @Test void cancellationRequiresScheduledOrderAndShipment(){
        assertTrue(PostPurchaseCancellationRules.eligible("FULFILLMENT_SCHEDULED","SCHEDULED"));
        assertFalse(PostPurchaseCancellationRules.eligible("IN_TRANSIT","SCHEDULED"));
        assertFalse(PostPurchaseCancellationRules.eligible("FULFILLMENT_SCHEDULED","HANDED_OFF"));
        assertFalse(PostPurchaseCancellationRules.eligible("FULFILLMENT_SCHEDULED","CANCEL_CLAIMED"));
    }
    @Test void onlyCustomerRequestReasonIsAccepted(){
        assertDoesNotThrow(()->PostPurchaseCancellationRules.requireCustomerReason("CUSTOMER_REQUEST"));
        assertThrows(IllegalArgumentException.class,()->PostPurchaseCancellationRules.requireCustomerReason("POLICY_OVERRIDE"));
    }
    @Test void downstreamOperationIdsAreStableAndDistinctByPurpose(){
        UUID operation=UUID.fromString("88000000-0000-4000-8000-000000000001");
        assertEquals(PostPurchaseCancellationRules.operationId(operation,"refund"),PostPurchaseCancellationRules.operationId(operation,"refund"));
        assertNotEquals(PostPurchaseCancellationRules.operationId(operation,"refund"),PostPurchaseCancellationRules.operationId(operation,"restock"));
    }
}
