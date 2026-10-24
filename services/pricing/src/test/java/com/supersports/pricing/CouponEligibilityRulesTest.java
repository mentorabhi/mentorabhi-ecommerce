package com.supersports.pricing;
import static org.assertj.core.api.Assertions.assertThat;
import java.util.Map;
import org.junit.jupiter.api.Test;
class CouponEligibilityRulesTest {
    @Test void categoryRulesRestrictEligibleLinesAndMissingRulesApplyToAll(){
        assertThat(CouponEligibilityRules.eligible("cricket-equipment",Map.of("categorySlugs",java.util.List.of("cricket-equipment")))).isTrue();
        assertThat(CouponEligibilityRules.eligible("football-equipment",Map.of("categorySlugs",java.util.List.of("cricket-equipment")))).isFalse();
        assertThat(CouponEligibilityRules.eligible("football-equipment",Map.of())).isTrue();
    }
}
