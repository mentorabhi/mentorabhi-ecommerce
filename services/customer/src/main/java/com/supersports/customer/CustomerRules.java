package com.supersports.customer;

import java.util.regex.Pattern;

final class CustomerRules {
    private static final Pattern INDIAN_PIN = Pattern.compile("[1-9][0-9]{5}");
    private CustomerRules() {}

    static int quantity(int value) {
        if (value < 1 || value > 99) throw new IllegalArgumentException("Quantity must be between 1 and 99");
        return value;
    }

    static AddressInput validateAddress(AddressInput address) {
        required(address.line1(), "Address line 1", 200);
        required(address.city(), "City", 100);
        required(address.state(), "State", 100);
        if (address.country() == null || !address.country().equalsIgnoreCase("IN"))
            throw new IllegalArgumentException("Only Indian addresses are supported currently");
        if (address.postalCode() == null || !INDIAN_PIN.matcher(address.postalCode().trim()).matches())
            throw new IllegalArgumentException("Enter a valid six-digit Indian PIN code");
        return new AddressInput(address.line1().trim(), address.city().trim(), address.state().trim(), address.postalCode().trim(), "IN",
                optional(address.line2(), "Address line 2", 200), optional(address.fullName(), "Full name", 200), optional(address.phone(), "Phone", 40), address.expectedRevision());
    }

    private static String required(String value, String label, int maximum) {
        if (value == null || value.isBlank() || value.trim().length() > maximum)
            throw new IllegalArgumentException(label + " is required and must be " + maximum + " characters or fewer");
        return value;
    }

    private static String optional(String value, String label, int maximum) {
        String normalized = value == null ? "" : value.trim();
        if (normalized.length() > maximum) throw new IllegalArgumentException(label + " must be " + maximum + " characters or fewer");
        return normalized;
    }

    record AddressInput(String line1, String city, String state, String postalCode, String country,
                        String line2, String fullName, String phone, int expectedRevision) {
        AddressInput(String line1, String city, String state, String postalCode, String country) {
            this(line1, city, state, postalCode, country, "", "", "", 1);
        }
    }
}
