package com.supersports.orders;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.UUID;

final class CheckoutRules {
    private CheckoutRules() {}
    static String validateKey(String key) {
        if (key == null || !key.matches("[A-Za-z0-9._:-]{8,120}")) throw new IllegalArgumentException("A valid Idempotency-Key is required");
        return key;
    }
    static Map<UUID,Integer> normalize(List<LineInput> lines) {
        if (lines == null || lines.isEmpty() || lines.size() > 50) throw new IllegalArgumentException("Checkout requires 1 to 50 item lines");
        var merged = new TreeMap<UUID,Integer>();
        for (var line : lines) {
            if (line == null || line.skuId() == null || line.quantity() == null || line.quantity() <= 0 || line.quantity() > 100)
                throw new IllegalArgumentException("Invalid checkout item");
            try { merged.merge(UUID.fromString(line.skuId()), line.quantity(), Math::addExact); }
            catch (ArithmeticException | IllegalArgumentException e) { throw new IllegalArgumentException("Invalid or excessive checkout quantity"); }
        }
        if (merged.values().stream().anyMatch(q -> q > 100)) throw new IllegalArgumentException("Per-SKU quantity exceeds 100");
        return Map.copyOf(merged);
    }
    static String payloadHash(Map<UUID,Integer> lines, String coupon) {
        String canonical = lines.entrySet().stream().sorted(Map.Entry.comparingByKey())
                .map(e -> e.getKey() + ":" + e.getValue()).collect(java.util.stream.Collectors.joining(","))
                + "|" + (coupon == null ? "" : coupon.trim().toUpperCase(java.util.Locale.ROOT));
        try { return java.util.HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(canonical.getBytes(StandardCharsets.UTF_8))); }
        catch (NoSuchAlgorithmException impossible) { throw new IllegalStateException(impossible); }
    }
    static boolean quoteExpired(Object expiresAt, java.time.Instant now) {
        try { return expiresAt == null || !java.time.Instant.parse(expiresAt.toString()).isAfter(now); }
        catch (java.time.DateTimeException invalid) { return true; }
    }
    record LineInput(String skuId,Integer quantity) {}
    record CheckoutInput(List<LineInput> lines,String couponCode) {}
}
