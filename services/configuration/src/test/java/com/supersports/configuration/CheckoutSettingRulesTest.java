package com.supersports.configuration;

import static org.assertj.core.api.Assertions.*;
import org.junit.jupiter.api.Test;

class CheckoutSettingRulesTest {
    @Test void normalizesValidatedSimulationValues(){
        assertThat(CheckoutSettingRules.normalize("tax.rate-bps"," 1800 ")).isEqualTo("1800");
        assertThat(CheckoutSettingRules.normalize("shipping.INR","0")).isEqualTo("0");
        assertThat(CheckoutSettingRules.normalize("inventory.reservation-seconds","600")).isEqualTo("600");
        assertThat(CheckoutSettingRules.normalize("payment.authorization-mode","DECLINE")).isEqualTo("DECLINE");
    }
    @Test void rejectsOutOfRangeAndUnknownSettings(){
        for(var input:new String[][]{{"tax.rate-bps","10001"},{"tax.rate-bps","-1"},{"shipping.USD","bad"},{"inventory.reservation-seconds","59"},{"payment.authorization-mode","REAL"},{"store.currency","USD"}})
            assertThatThrownBy(()->CheckoutSettingRules.normalize(input[0],input[1])).isInstanceOf(IllegalArgumentException.class);
    }
}
