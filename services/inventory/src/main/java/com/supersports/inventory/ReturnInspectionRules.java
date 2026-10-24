package com.supersports.inventory;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Comparator;
import java.util.HexFormat;
import java.util.List;
import java.util.Set;
import java.util.UUID;

final class ReturnInspectionRules {
    private static final Set<String> CONDITIONS=Set.of("SELLABLE","DAMAGED","DISPUTED");
    private ReturnInspectionRules(){}
    static List<Decision> validate(List<Decision> decisions,List<UnitKey> received){
        if(decisions==null||received==null||received.isEmpty()||decisions.size()!=received.size())throw new IllegalArgumentException("Every received return unit needs one inspection decision");
        var expected=received.stream().map(unit->unit.skuId()+":"+unit.ordinal()).collect(java.util.stream.Collectors.toSet());
        var seen=new java.util.HashSet<String>();
        for(var decision:decisions){if(decision==null||decision.skuId()==null||decision.ordinal()<0||!CONDITIONS.contains(decision.condition())||decision.reason()==null||decision.reason().isBlank()||decision.reason().length()>500)throw new IllegalArgumentException("Invalid inspection decision");
            if(!seen.add(decision.skuId()+":"+decision.ordinal()))throw new IllegalArgumentException("Duplicate inspected unit");}
        if(!seen.equals(expected))throw new IllegalArgumentException("Inspection manifest differs from received units");
        return decisions.stream().sorted(Comparator.comparing((Decision decision)->decision.skuId().toString()).thenComparingInt(Decision::ordinal)).toList();
    }
    static String hash(List<Decision> decisions){
        String canonical=decisions.stream().sorted(Comparator.comparing((Decision decision)->decision.skuId().toString()).thenComparingInt(Decision::ordinal)).map(decision->decision.skuId()+":"+decision.ordinal()+":"+decision.condition()+":"+decision.reason().trim()).collect(java.util.stream.Collectors.joining("|"));
        try{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(canonical.getBytes(StandardCharsets.UTF_8)));}
        catch(java.security.NoSuchAlgorithmException impossible){throw new IllegalStateException("SHA-256 is unavailable",impossible);}
    }
    static String hashUnits(List<UnitKey> units){String canonical=units.stream().sorted(Comparator.comparing((UnitKey unit)->unit.skuId().toString()).thenComparingInt(UnitKey::ordinal)).map(unit->unit.skuId()+":"+unit.ordinal()).collect(java.util.stream.Collectors.joining("|"));try{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(canonical.getBytes(StandardCharsets.UTF_8)));}catch(java.security.NoSuchAlgorithmException impossible){throw new IllegalStateException("SHA-256 is unavailable",impossible);}}
    record UnitKey(UUID skuId,int ordinal){}
    record Decision(UUID skuId,int ordinal,String condition,String reason){}
}
