package com.supersports.pricing;
import tools.jackson.databind.json.JsonMapper;
final class Json {private static final JsonMapper M=new JsonMapper();private Json(){}static String write(Object o){try{return M.writeValueAsString(o);}catch(tools.jackson.core.JacksonException e){throw new IllegalArgumentException("Invalid JSON value",e);}}}
