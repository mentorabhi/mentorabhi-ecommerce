package com.supersports.pricing;
import static org.assertj.core.api.Assertions.assertThat;
import java.util.Map;
import org.junit.jupiter.api.Test;
class CouponEligibilityRulesTest {
    @Test void categoryRulesRestrictEligibleLinesAndMissingRulesApplyToAll(){
        assertThat(CouponEligibilityRules.eligible("model-1","cricket-equipment",Map.of("categorySlugs",java.util.List.of("cricket-equipment")))).isTrue();
        assertThat(CouponEligibilityRules.eligible("model-1","football-equipment",Map.of("categorySlugs",java.util.List.of("cricket-equipment")))).isFalse();
        assertThat(CouponEligibilityRules.eligible("model-1","football-equipment",Map.of())).isTrue();
    }
    @Test void productAllowlistAppliesOnlyToSelectedModelsAndCombinesWithCategory(){
        var rules=Map.<String,Object>of("productIds",java.util.List.of("model-1"),"categorySlugs",java.util.List.of("cricket-equipment"));
        assertThat(CouponEligibilityRules.eligible("model-1","cricket-equipment",rules)).isTrue();
        assertThat(CouponEligibilityRules.eligible("model-2","cricket-equipment",rules)).isFalse();
        assertThat(CouponEligibilityRules.eligible("model-1","football-equipment",rules)).isFalse();
        assertThat(CouponEligibilityRules.eligible("model-1","cricket-equipment",Map.of("productIds",java.util.List.of()))).isFalse();
        assertThat(CouponEligibilityRules.eligible("model-1","cricket-equipment",Map.of("productIds","model-1"))).isFalse();
    }
}
