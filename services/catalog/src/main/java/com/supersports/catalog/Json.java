package com.supersports.catalog;

import tools.jackson.databind.json.JsonMapper;

final class Json {
    private static final JsonMapper MAPPER = new JsonMapper();
    private Json() {}
    static String write(Object value) {
        try { return MAPPER.writeValueAsString(value); }
        catch (tools.jackson.core.JacksonException e) { throw new IllegalArgumentException("Value cannot be encoded as JSON", e); }
    }
    static Object read(String value) {
        try { return MAPPER.readValue(value, Object.class); }
        catch (tools.jackson.core.JacksonException e) { throw new IllegalArgumentException("Stored JSON is invalid", e); }
    }
}
