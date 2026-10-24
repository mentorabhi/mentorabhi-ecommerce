package com.supersports.orders;

import java.math.BigDecimal;
import java.math.RoundingMode;

final class CheckoutMoney {
    private CheckoutMoney() {}
    static long tax(long merchandiseAfterDiscountMinor,int rateBps){
        if(merchandiseAfterDiscountMinor<0||rateBps<0||rateBps>10000)throw new IllegalArgumentException("Invalid tax input");
        return BigDecimal.valueOf(merchandiseAfterDiscountMinor).multiply(BigDecimal.valueOf(rateBps))
                .divide(BigDecimal.valueOf(10000),0,RoundingMode.HALF_UP).longValueExact();
    }
    static long total(long merchandiseAfterDiscountMinor,long taxMinor,long shippingMinor){
        if(merchandiseAfterDiscountMinor<0||taxMinor<0||shippingMinor<0)throw new IllegalArgumentException("Invalid checkout total input");
        return Math.addExact(Math.addExact(merchandiseAfterDiscountMinor,taxMinor),shippingMinor);
    }
}
