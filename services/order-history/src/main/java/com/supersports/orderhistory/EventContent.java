package com.supersports.orderhistory;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import tools.jackson.databind.json.JsonMapper;

final class EventContent {
    private static final JsonMapper JSON = new JsonMapper();
    private EventContent() {}

    static Map<String,Object> read(String raw) {
        try { return JSON.readValue(raw, Map.class); }
        catch (RuntimeException error) { throw new IllegalArgumentException("INVALID_EVENT_JSON"); }
    }

    static String write(Object value) { return JSON.writeValueAsString(value); }
    static String hash(String raw) { return rawHash(write(canonical(read(raw)))); }
    static String rawHash(String value) {
        try { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8))); }
        catch (java.security.NoSuchAlgorithmException error) { throw new IllegalStateException(error); }
    }

    private static Object canonical(Object value) {
        if (value instanceof Map<?,?> object) {
            var sorted = new TreeMap<String,Object>();
            object.forEach((key, child) -> sorted.put(key.toString(), canonical(child)));
            return sorted;
        }
        if (value instanceof List<?> array) return array.stream().map(EventContent::canonical).toList();
        if (value instanceof Number number) {
            var normalized=new java.math.BigDecimal(number.toString()).stripTrailingZeros();
            return normalized.scale()<=0?normalized.toBigIntegerExact():normalized;
        }
        return value;
    }
}
