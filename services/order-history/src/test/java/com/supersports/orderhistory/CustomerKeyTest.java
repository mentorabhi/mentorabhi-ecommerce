package com.supersports.orderhistory;

import static org.junit.jupiter.api.Assertions.*;
import org.junit.jupiter.api.Test;

class CustomerKeyTest {
    private static final String SECRET = "a-local-order-history-key-long-enough-for-hmac";

    @Test void sameSubjectHasStableOpaqueKeyAndSubjectsRemainSeparated() {
        CustomerKey keys = new CustomerKey(SECRET);
        String first = keys.forSubject("customer-a");
        assertEquals(first, keys.forSubject("customer-a"));
        assertNotEquals(first, keys.forSubject("customer-b"));
        assertEquals(64, first.length());
        assertFalse(first.contains("customer-a"));
    }

    @Test void rejectsWeakKey() {
        assertThrows(IllegalArgumentException.class, () -> new CustomerKey("too-short"));
    }
}
