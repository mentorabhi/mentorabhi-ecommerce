package com.supersports.inventory;

/** Checked arithmetic and availability rules shared by reservation operations. */
final class InventoryReservationRules {
    private InventoryReservationRules() {}

    static long available(long onHand, long reserved) {
        if (onHand < 0 || reserved < 0 || reserved > onHand)
            throw new IllegalArgumentException("Invalid stock or reservation quantity");
        return Math.subtractExact(onHand, reserved);
    }

    static boolean canReserve(long onHand, long requested, long reserved) {
        if (requested <= 0) throw new IllegalArgumentException("Reservation quantity must be positive");
        return requested <= available(onHand, reserved);
    }

    static long committedOnHand(long onHand, long quantity) {
        if (onHand < 0 || quantity <= 0 || quantity > onHand)
            throw new IllegalArgumentException("Invalid committed quantity");
        return Math.subtractExact(onHand, quantity);
    }
}
