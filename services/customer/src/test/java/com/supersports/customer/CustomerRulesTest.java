package com.supersports.customer;

import org.junit.jupiter.api.Test;
import static org.assertj.core.api.Assertions.*;

class CustomerRulesTest {
    @Test void acceptsBoundedCartQuantities() {
        assertThat(CustomerRules.quantity(1)).isEqualTo(1);
        assertThat(CustomerRules.quantity(99)).isEqualTo(99);
    }

    @Test void rejectsCartQuantitiesOutsideSupportedRange() {
        assertThatIllegalArgumentException().isThrownBy(() -> CustomerRules.quantity(0));
        assertThatIllegalArgumentException().isThrownBy(() -> CustomerRules.quantity(100));
    }

    @Test void requiresCompleteIndianAddressAndSixDigitPin() {
        var address = new CustomerRules.AddressInput("18 Race Course Road", "Bengaluru", "Karnataka", "560001", "IN");
        assertThat(CustomerRules.validateAddress(address)).isEqualTo(address);
        assertThatIllegalArgumentException().isThrownBy(() -> CustomerRules.validateAddress(
                new CustomerRules.AddressInput("18 Race Course Road", "Bengaluru", "", "560001", "IN")));
        assertThatIllegalArgumentException().isThrownBy(() -> CustomerRules.validateAddress(
                new CustomerRules.AddressInput("18 Race Course Road", "Bengaluru", "Karnataka", "012345", "IN")));
        assertThatIllegalArgumentException().isThrownBy(() -> CustomerRules.validateAddress(
                new CustomerRules.AddressInput("18 Race Course Road", "Bengaluru", "Karnataka", "560001", "US")));
        assertThatIllegalArgumentException().isThrownBy(() -> CustomerRules.validateAddress(
                new CustomerRules.AddressInput("18 Race Course Road", "Bengaluru", "Karnataka", "560001", "IN", "", "x".repeat(201), "", 1)));
    }
}
