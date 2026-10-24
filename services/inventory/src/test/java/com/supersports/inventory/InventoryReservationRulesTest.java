package com.supersports.inventory;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class InventoryReservationRulesTest {
    @Test
    void availabilityExcludesActiveReservationsWithoutChangingOnHand() {
        assertThat(InventoryReservationRules.available(8, 3)).isEqualTo(5);
    }

    @Test
    void cannotReserveMoreThanTheUnreservedQuantity() {
        assertThat(InventoryReservationRules.canReserve(8, 6, 3)).isFalse();
        assertThat(InventoryReservationRules.canReserve(8, 5, 3)).isTrue();
    }

    @Test
    void reservationCommitDecrementsOnHandExactlyOnce() {
        assertThat(InventoryReservationRules.committedOnHand(8, 3)).isEqualTo(5);
        assertThatThrownBy(() -> InventoryReservationRules.committedOnHand(2, 3))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void rejectsInvalidOrOverflowingReservationQuantities() {
        assertThatThrownBy(() -> InventoryReservationRules.available(2, -1))
                .isInstanceOf(IllegalArgumentException.class);
        assertThat(InventoryReservationRules.available(Long.MAX_VALUE, 1)).isEqualTo(Long.MAX_VALUE - 1);
    }
}
