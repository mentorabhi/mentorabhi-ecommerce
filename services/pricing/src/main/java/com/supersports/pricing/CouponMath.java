package com.supersports.pricing;

import java.math.BigInteger;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;

/** Deterministic minor-unit coupon arithmetic; all rounding is half-up. */
final class CouponMath {
    private CouponMath() {}

    static long discount(String kind, long value, long eligibleSubtotal, Long maximum) {
        if (value < 0 || eligibleSubtotal < 0 || (maximum != null && maximum < 0))
            throw new IllegalArgumentException("Coupon values cannot be negative");
        long raw = switch (kind) {
            case "PERCENT" -> BigInteger.valueOf(eligibleSubtotal).multiply(BigInteger.valueOf(value))
                    .add(BigInteger.valueOf(5000)).divide(BigInteger.valueOf(10000)).longValueExact();
            case "FIXED" -> value;
            default -> throw new IllegalArgumentException("Unsupported coupon kind");
        };
        return Math.min(eligibleSubtotal, maximum == null ? raw : Math.min(raw, maximum));
    }

    static Map<UUID, Long> allocate(long discount, Map<UUID, Long> subtotals) {
        long total = 0;
        for (long amount : subtotals.values()) {
            if (amount < 0) throw new IllegalArgumentException("Line subtotal cannot be negative");
            total = Math.addExact(total, amount);
        }
        if (discount < 0 || discount > total || (total == 0 && discount != 0))
            throw new IllegalArgumentException("Discount exceeds eligible subtotal");
        var result = new LinkedHashMap<UUID, Long>();
        var remainders = new java.util.ArrayList<Map.Entry<UUID, BigInteger>>();
        long allocated = 0;
        for (var line : subtotals.entrySet()) {
            BigInteger product = BigInteger.valueOf(discount).multiply(BigInteger.valueOf(line.getValue()));
            BigInteger[] qr = product.divideAndRemainder(BigInteger.valueOf(total == 0 ? 1 : total));
            long share = qr[0].longValueExact();
            result.put(line.getKey(), share);
            allocated = Math.addExact(allocated, share);
            remainders.add(Map.entry(line.getKey(), qr[1]));
        }
        remainders.sort(Comparator.<Map.Entry<UUID, BigInteger>, BigInteger>comparing(Map.Entry::getValue).reversed()
                .thenComparing(Map.Entry::getKey));
        for (long left = discount - allocated, i = 0; left > 0; left--, i++) {
            UUID sku = remainders.get(Math.toIntExact(i % remainders.size())).getKey();
            result.put(sku, Math.addExact(result.get(sku), 1));
        }
        return result;
    }
}
