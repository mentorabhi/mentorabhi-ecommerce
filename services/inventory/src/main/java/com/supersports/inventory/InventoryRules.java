package com.supersports.inventory;
final class InventoryRules{
 private InventoryRules(){}
 static void validateAdjustment(long delta,String reason,String key){if(delta==0||reason==null||reason.isBlank()||key==null||!key.matches("[A-Za-z0-9._:-]{8,120}"))throw new IllegalArgumentException("Nonzero delta, reason and valid idempotency key are required");}
 static long resultingStock(long current,long delta){long result;try{result=Math.addExact(current,delta);}catch(ArithmeticException e){throw new IllegalArgumentException("Stock quantity overflow",e);}if(result<0)throw new IllegalArgumentException("Adjustment would make stock negative");return result;}
}
