package com.supersports.orders;

import static org.assertj.core.api.Assertions.*;
import org.junit.jupiter.api.Test;

class CheckoutMoneyTest {
    @Test void taxRoundsHalfUpOnceOnDiscountedMerchandise(){
        assertThat(CheckoutMoney.tax(1001,1800)).isEqualTo(180);
        assertThat(CheckoutMoney.tax(3,5000)).isEqualTo(2);
    }
    @Test void checkedTotalCannotWrapOrAcceptNegativeComponents(){
        assertThat(CheckoutMoney.total(100,18,99)).isEqualTo(217);
        assertThatThrownBy(()->CheckoutMoney.total(Long.MAX_VALUE,1,0)).isInstanceOf(ArithmeticException.class);
        assertThatThrownBy(()->CheckoutMoney.tax(-1,1800)).isInstanceOf(IllegalArgumentException.class);
    }
}
