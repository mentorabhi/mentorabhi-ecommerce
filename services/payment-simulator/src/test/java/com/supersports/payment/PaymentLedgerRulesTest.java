package com.supersports.payment;

import static org.junit.jupiter.api.Assertions.*;
import java.util.List;
import org.junit.jupiter.api.Test;

class PaymentLedgerRulesTest {
    private static PaymentLedgerRules.Fact fact(String operation,long amount,String currency,String state){return new PaymentLedgerRules.Fact(operation,amount,currency,state);}
    private static final List<PaymentLedgerRules.Fact> AUTH=List.of(fact("AUTHORIZE",100,"INR","AUTHORIZED"));
    private static final List<PaymentLedgerRules.Fact> CAPTURED=List.of(AUTH.getFirst(),fact("CAPTURE",100,"INR","CAPTURED"));

    @Test void supportsZeroValueCheckoutAndOneAuthorizationDecision(){
        assertEquals("AUTHORIZED",PaymentLedgerRules.decide("AUTHORIZE",0,"INR","APPROVE",List.of()));
        assertEquals("CAPTURED",PaymentLedgerRules.decide("CAPTURE",0,"INR","APPROVE",List.of(fact("AUTHORIZE",0,"INR","AUTHORIZED"))));
        assertThrows(IllegalStateException.class,()->PaymentLedgerRules.decide("AUTHORIZE",100,"INR","APPROVE",AUTH));
    }
    @Test void captureMustBeSingleFullAmountAndCurrency(){
        assertEquals("CAPTURED",PaymentLedgerRules.decide("CAPTURE",100,"INR","APPROVE",AUTH));
        assertThrows(IllegalStateException.class,()->PaymentLedgerRules.decide("CAPTURE",99,"INR","APPROVE",AUTH));
        assertThrows(IllegalStateException.class,()->PaymentLedgerRules.decide("CAPTURE",100,"USD","APPROVE",AUTH));
        assertThrows(IllegalStateException.class,()->PaymentLedgerRules.decide("CAPTURE",100,"INR","APPROVE",List.of(AUTH.getFirst(),fact("CAPTURE",100,"INR","CAPTURED"))));
    }
    @Test void voidBlocksLaterCaptureAndCannotFollowCapture(){
        var voided=List.of(AUTH.getFirst(),fact("VOID",100,"INR","VOIDED"));
        assertThrows(IllegalStateException.class,()->PaymentLedgerRules.decide("CAPTURE",100,"INR","APPROVE",voided));
        assertThrows(IllegalStateException.class,()->PaymentLedgerRules.decide("VOID",100,"INR","APPROVE",CAPTURED));
        assertEquals("VOIDED",PaymentLedgerRules.decide("VOID",100,"INR","APPROVE",AUTH));
    }
    @Test void cumulativeRefundsCannotExceedCaptureAndCurrencyMustMatch(){
        var partlyRefunded=List.of(CAPTURED.get(0),CAPTURED.get(1),fact("REFUND",60,"INR","REFUNDED"));
        assertEquals("REFUNDED",PaymentLedgerRules.decide("REFUND",40,"INR","APPROVE",partlyRefunded));
        assertThrows(IllegalStateException.class,()->PaymentLedgerRules.decide("REFUND",41,"INR","APPROVE",partlyRefunded));
        assertThrows(IllegalStateException.class,()->PaymentLedgerRules.decide("REFUND",10,"USD","APPROVE",CAPTURED));
        assertThrows(IllegalStateException.class,()->PaymentLedgerRules.decide("REFUND",0,"INR","APPROVE",CAPTURED));
    }
    @Test void declineCannotCapture(){
        var declined=List.of(fact("AUTHORIZE",100,"INR","DECLINED"));
        assertThrows(IllegalStateException.class,()->PaymentLedgerRules.decide("CAPTURE",100,"INR","APPROVE",declined));
    }
}
