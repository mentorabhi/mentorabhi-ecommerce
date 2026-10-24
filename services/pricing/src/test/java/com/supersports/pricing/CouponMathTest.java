package com.supersports.pricing;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class CouponMathTest {
    @Test
    void percentageDiscountRoundsHalfUpAndHonorsMaximum() {
        assertThat(CouponMath.discount("PERCENT", 1000, 105, null)).isEqualTo(11);
        assertThat(CouponMath.discount("PERCENT", 5000, 101, 40L)).isEqualTo(40);
    }

    @Test
    void fixedDiscountCannotExceedEligibleSubtotal() {
        assertThat(CouponMath.discount("FIXED", 500, 320, null)).isEqualTo(320);
    }

    @Test
    void allocatesDiscountProportionallyAndConservesEveryMinorUnit() {
        var smaller = UUID.fromString("00000000-0000-4000-8000-000000000001");
        var larger = UUID.fromString("00000000-0000-4000-8000-000000000002");
        Map<UUID, Long> subtotals = new LinkedHashMap<>();
        subtotals.put(larger, 2L);
        subtotals.put(smaller, 3L);

        assertThat(CouponMath.allocate(1, subtotals))
                .containsExactly(Map.entry(larger, 0L), Map.entry(smaller, 1L));
    }

    @Test
    void breaksEqualRemainderTiesBySkuIdAndNeverExceedsLineSubtotal() {
        var first = UUID.fromString("00000000-0000-4000-8000-000000000001");
        var second = UUID.fromString("00000000-0000-4000-8000-000000000002");
        Map<UUID, Long> subtotals = new LinkedHashMap<>();
        subtotals.put(second, 1L);
        subtotals.put(first, 1L);

        assertThat(CouponMath.allocate(1, subtotals))
                .containsExactly(Map.entry(second, 0L), Map.entry(first, 1L));
    }
}
