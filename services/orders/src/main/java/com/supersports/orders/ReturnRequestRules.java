package com.supersports.orders;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;

final class ReturnRequestRules {
    private ReturnRequestRules(){}
    static Map<UUID,Integer> normalize(java.util.List<LineInput> lines){
        if(lines==null||lines.isEmpty()||lines.size()>50)throw new IllegalArgumentException("Return lines are required");
        var normalized=new LinkedHashMap<UUID,Integer>();
        for(var line:lines){if(line==null||line.skuId()==null||line.quantity()<1||line.quantity()>100)throw new IllegalArgumentException("Invalid return quantity");
            UUID sku=UUID.fromString(line.skuId());if(normalized.putIfAbsent(sku,line.quantity())!=null)throw new IllegalArgumentException("Duplicate return SKU");}
        return Map.copyOf(normalized);
    }
    static String payloadHash(Map<UUID,Integer> lines){
        try{String canonical=lines.entrySet().stream().sorted(Map.Entry.comparingByKey()).map(e->e.getKey()+":"+e.getValue()).collect(java.util.stream.Collectors.joining("|"));return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(canonical.getBytes(StandardCharsets.UTF_8)));}
        catch(java.security.NoSuchAlgorithmException impossible){throw new IllegalStateException("SHA-256 is unavailable",impossible);}
    }
    static boolean withinWindow(Instant deliveredAt,Instant now,long days){return deliveredAt!=null&&now!=null&&days>=1&&days<=90&&!now.isAfter(deliveredAt.plusSeconds(Math.multiplyExact(days,86400)));}
    record LineInput(String skuId,int quantity){}
}
