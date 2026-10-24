package com.supersports.orders;
import static org.assertj.core.api.Assertions.*;
import java.util.List;
import org.junit.jupiter.api.Test;
class CheckoutRulesTest {
    @Test void canonicalHashIgnoresLineOrderingAndCouponCase(){
        var a=CheckoutRules.normalize(List.of(new CheckoutRules.LineInput("00000000-0000-4000-8000-000000000001",1),new CheckoutRules.LineInput("00000000-0000-4000-8000-000000000002",2)));
        var b=CheckoutRules.normalize(List.of(new CheckoutRules.LineInput("00000000-0000-4000-8000-000000000002",2),new CheckoutRules.LineInput("00000000-0000-4000-8000-000000000001",1)));
        assertThat(CheckoutRules.payloadHash(a," save10 ")).isEqualTo(CheckoutRules.payloadHash(b,"SAVE10"));
    }
    @Test void duplicateSkusAreCombinedAndQuantitiesBounded(){
        var lines=CheckoutRules.normalize(List.of(new CheckoutRules.LineInput("00000000-0000-4000-8000-000000000001",2),new CheckoutRules.LineInput("00000000-0000-4000-8000-000000000001",3)));
        assertThat(lines.values()).containsExactly(5);
        assertThatThrownBy(()->CheckoutRules.normalize(List.of(new CheckoutRules.LineInput("00000000-0000-4000-8000-000000000001",60),new CheckoutRules.LineInput("00000000-0000-4000-8000-000000000001",60)))).isInstanceOf(IllegalArgumentException.class);
    }
    @Test void rejectsBadKeysAndInvalidQuantities(){
        assertThatThrownBy(()->CheckoutRules.validateKey("bad key")).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(()->CheckoutRules.normalize(List.of(new CheckoutRules.LineInput("not-a-uuid",1)))).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(()->CheckoutRules.normalize(List.of(new CheckoutRules.LineInput("00000000-0000-4000-8000-000000000001",0)))).isInstanceOf(IllegalArgumentException.class);
    }
    @Test void expiredOrInvalidQuoteCannotStartInventoryReservation(){
        var now=java.time.Instant.parse("2026-10-24T12:00:00Z");
        assertThat(CheckoutRules.quoteExpired("2026-10-24T11:59:59Z",now)).isTrue();
        assertThat(CheckoutRules.quoteExpired(null,now)).isTrue();
        assertThat(CheckoutRules.quoteExpired("not-a-timestamp",now)).isTrue();
        assertThat(CheckoutRules.quoteExpired("2026-10-24T12:00:01Z",now)).isFalse();
    }
}
