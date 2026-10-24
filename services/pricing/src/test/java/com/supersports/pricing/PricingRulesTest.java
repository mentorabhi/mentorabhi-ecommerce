package com.supersports.pricing;
import java.time.Instant;
import java.util.Map;
import org.junit.jupiter.api.Test;
import static org.assertj.core.api.Assertions.*;
class PricingRulesTest {
 @Test void rejectsMalformedCouponIntervalsAndDiscounts(){var now=Instant.now().toString();var bad=new PricingRepository.CouponInput("SAVE",true,now,now,"INR","PERCENT",10001,0,null,null,null,Map.of());assertThatThrownBy(()->PricingController.validate(bad)).isInstanceOf(IllegalArgumentException.class).hasMessageContaining("end");var later=new PricingRepository.CouponInput("SAVE",true,now,Instant.parse(now).plusSeconds(60).toString(),"INR","PERCENT",10001,0,null,null,null,Map.of());assertThatThrownBy(()->PricingController.validate(later)).isInstanceOf(IllegalArgumentException.class).hasMessageContaining("discount");}
}
