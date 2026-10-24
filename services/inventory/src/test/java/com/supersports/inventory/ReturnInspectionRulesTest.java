package com.supersports.inventory;

import static org.junit.jupiter.api.Assertions.*;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class ReturnInspectionRulesTest {
    private static final UUID SKU=UUID.fromString("00000000-0000-4000-8000-000000000001");
    @Test void requiresACompleteUniqueManifestAndStableReplayHash(){
        var units=List.of(new ReturnInspectionRules.UnitKey(SKU,0),new ReturnInspectionRules.UnitKey(SKU,1));
        var decisions=List.of(new ReturnInspectionRules.Decision(SKU,1,"DAMAGED","sole split"),new ReturnInspectionRules.Decision(SKU,0,"SELLABLE","unused"));
        assertEquals(2,ReturnInspectionRules.validate(decisions,units).size());
        assertEquals(ReturnInspectionRules.hash(decisions),ReturnInspectionRules.hash(List.of(decisions.get(1),decisions.get(0))));
        assertThrows(IllegalArgumentException.class,()->ReturnInspectionRules.validate(List.of(decisions.get(0)),units));
        assertThrows(IllegalArgumentException.class,()->ReturnInspectionRules.validate(List.of(decisions.get(0),decisions.get(0)),units));
    }
    @Test void rejectsUnsupportedConditionAndMissingReason(){
        var unit=List.of(new ReturnInspectionRules.UnitKey(SKU,0));
        assertThrows(IllegalArgumentException.class,()->ReturnInspectionRules.validate(List.of(new ReturnInspectionRules.Decision(SKU,0,"REFUND","reason")),unit));
        assertThrows(IllegalArgumentException.class,()->ReturnInspectionRules.validate(List.of(new ReturnInspectionRules.Decision(SKU,0,"SELLABLE"," ")),unit));
    }
}
