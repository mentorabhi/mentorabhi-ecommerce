package com.supersports.orders;
import tools.jackson.databind.json.JsonMapper;
final class OrdersJson {
    private static final JsonMapper MAPPER=new JsonMapper();
    private OrdersJson(){}
    static String write(Object value){try{return MAPPER.writeValueAsString(value);}catch(tools.jackson.core.JacksonException e){throw new IllegalArgumentException("Invalid JSON",e);}}
    @SuppressWarnings("unchecked") static java.util.Map<String,Object> readMap(Object value){try{String json;if(value instanceof String s)json=s;else{try{json=(String)value.getClass().getMethod("getValue").invoke(value);}catch(ReflectiveOperationException ignored){json=String.valueOf(value);}}return (java.util.Map<String,Object>)MAPPER.readValue(json,Object.class);}catch(tools.jackson.core.JacksonException e){throw new IllegalArgumentException("Invalid stored JSON",e);}}
}
