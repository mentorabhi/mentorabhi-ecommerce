package com.supersports.payment;

import java.util.List;
import java.math.BigInteger;

final class PaymentLedgerRules {
    private PaymentLedgerRules() {}

    static String decide(String operation,long amount,String currency,String mode,List<Fact> ledger) {
        if (amount < 0 || currency == null || !currency.matches("[A-Z]{3}")) throw new IllegalArgumentException("Invalid payment operation");
        if (!List.of("AUTHORIZE","CAPTURE","VOID","REFUND").contains(operation)) throw new IllegalArgumentException("Unsupported payment operation");
        if (!List.of("APPROVE","DECLINE").contains(mode)) throw new IllegalArgumentException("Invalid authorization mode");
        if (!operation.equals("AUTHORIZE") && !mode.equals("APPROVE")) throw new IllegalArgumentException("Authorization mode is only valid for authorization");

        var authorization=ledger.stream().filter(row->row.operation().equals("AUTHORIZE")).findFirst().orElse(null);
        var capture=ledger.stream().filter(row->row.operation().equals("CAPTURE")).findFirst().orElse(null);
        boolean voided=ledger.stream().anyMatch(row->row.operation().equals("VOID"));
        BigInteger refunded=ledger.stream().filter(row->row.operation().equals("REFUND"))
                .map(row->BigInteger.valueOf(row.amount())).reduce(BigInteger.ZERO,BigInteger::add);

        return switch(operation) {
            case "AUTHORIZE" -> {
                if (authorization!=null) throw state();
                yield mode.equals("DECLINE")?"DECLINED":"AUTHORIZED";
            }
            case "CAPTURE" -> {
                requireApproved(authorization);
                if (voided || capture!=null) throw state();
                requireSameTerms(authorization,amount,currency);
                yield "CAPTURED";
            }
            case "VOID" -> {
                requireApproved(authorization);
                if (voided || capture!=null) throw state();
                requireSameTerms(authorization,amount,currency);
                yield "VOIDED";
            }
            case "REFUND" -> {
                BigInteger proposed=refunded.add(BigInteger.valueOf(amount));
                if (capture==null || amount<=0 || !currency.equals(capture.currency()) || proposed.compareTo(BigInteger.valueOf(capture.amount()))>0) throw state();
                yield "REFUNDED";
            }
            default -> throw new IllegalArgumentException("Unsupported payment operation");
        };
    }

    private static void requireApproved(Fact authorization) {
        if (authorization==null || !authorization.state().equals("AUTHORIZED")) throw state();
    }
    private static void requireSameTerms(Fact authorization,long amount,String currency) {
        if (authorization.amount()!=amount || !authorization.currency().equals(currency)) throw state();
    }
    private static IllegalStateException state(){return new IllegalStateException("Payment state does not permit this operation");}
    record Fact(String operation,long amount,String currency,String state) {}
}
