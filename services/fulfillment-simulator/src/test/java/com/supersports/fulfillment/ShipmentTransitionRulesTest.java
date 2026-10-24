package com.supersports.fulfillment;

import static org.junit.jupiter.api.Assertions.*;
import org.junit.jupiter.api.Test;

class ShipmentTransitionRulesTest {
    @Test void permitsOnlyTheNextSimulatorMilestone(){
        assertTrue(ShipmentTransitionRules.permits("SCHEDULED","HANDED_OFF"));
        assertTrue(ShipmentTransitionRules.permits("HANDED_OFF","IN_TRANSIT"));
        assertTrue(ShipmentTransitionRules.permits("IN_TRANSIT","DELIVERED"));
        assertFalse(ShipmentTransitionRules.permits("SCHEDULED","DELIVERED"));
        assertFalse(ShipmentTransitionRules.permits("DELIVERED","IN_TRANSIT"));
        assertFalse(ShipmentTransitionRules.permits("CANCEL_CLAIMED","HANDED_OFF"));
        assertFalse(ShipmentTransitionRules.permits("SCHEDULED",null));
    }
}
