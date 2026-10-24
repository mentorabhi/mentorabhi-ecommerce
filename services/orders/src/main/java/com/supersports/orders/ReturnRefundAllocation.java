package com.supersports.orders;

import java.math.BigInteger;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

final class ReturnRefundAllocation {
    private ReturnRefundAllocation() {}
    static List<Unit> allocate(List<Line> lines,long taxTotal,Map<UUID,Integer> previouslyClaimed,Map<UUID,Integer> requested){
        if(lines==null||lines.isEmpty()||taxTotal<0||previouslyClaimed==null||requested==null)throw new IllegalArgumentException("Invalid return allocation");
        if(lines.stream().anyMatch(line->line==null||line.skuId()==null||line.quantity()<=0||line.lineTotalMinor()<0))throw new IllegalArgumentException("Invalid order line");
        var ordered=lines.stream().sorted(Comparator.comparing(line->line.skuId().toString())).toList();
        var skuSet=new java.util.HashSet<UUID>();for(Line line:ordered)if(!skuSet.add(line.skuId()))throw new IllegalArgumentException("Duplicate order line");
        if(requested.entrySet().stream().anyMatch(entry->entry.getKey()==null||entry.getValue()==null||entry.getValue()<=0||!skuSet.contains(entry.getKey())))throw new IllegalArgumentException("Invalid return quantities");
        BigInteger baseTotal=ordered.stream().map(line->BigInteger.valueOf(line.lineTotalMinor())).reduce(BigInteger.ZERO,BigInteger::add);
        if(baseTotal.signum()==0&&taxTotal!=0)throw new IllegalArgumentException("Tax cannot be allocated without merchandise value");
        Map<UUID,Long> lineTax=new HashMap<>();Map<UUID,BigInteger> remainders=new HashMap<>();long allocated=0;
        for(Line line:ordered){
            BigInteger[] qr=BigInteger.valueOf(taxTotal).multiply(BigInteger.valueOf(line.lineTotalMinor())).divideAndRemainder(baseTotal.signum()==0?BigInteger.ONE:baseTotal);
            long floor=qr[0].longValueExact();lineTax.put(line.skuId(),floor);remainders.put(line.skuId(),qr[1]);allocated=Math.addExact(allocated,floor);}
        long leftover=taxTotal-allocated;
        var taxOrder=ordered.stream().sorted(Comparator.<Line,BigInteger>comparing(line->remainders.get(line.skuId())).reversed().thenComparing(line->line.skuId().toString())).toList();
        for(int i=0;i<leftover;i++){Line line=taxOrder.get(i);lineTax.put(line.skuId(),lineTax.get(line.skuId())+1);}
        var result=new ArrayList<Unit>();
        for(Line line:ordered){int start=previouslyClaimed.getOrDefault(line.skuId(),0),count=requested.getOrDefault(line.skuId(),0);
            if(start<0||start>line.quantity()||count<=0||count>line.quantity()-start)throw new IllegalArgumentException("Return quantity exceeds purchased units");
            long merchandiseBase=line.lineTotalMinor()/line.quantity(),merchandiseRemainder=line.lineTotalMinor()%line.quantity();
            long tax=lineTax.get(line.skuId()),taxBase=tax/line.quantity(),taxRemainder=tax%line.quantity();
            for(int ordinal=start;ordinal<start+count;ordinal++)result.add(new Unit(line.skuId(),ordinal,merchandiseBase+(ordinal<merchandiseRemainder?1:0),taxBase+(ordinal<taxRemainder?1:0)));
        }
        return List.copyOf(result);
    }
    record Line(UUID skuId,int quantity,long lineTotalMinor){}
    record Unit(UUID skuId,int ordinal,long merchandiseMinor,long taxMinor){long refundMinor(){return Math.addExact(merchandiseMinor,taxMinor);}}
}
