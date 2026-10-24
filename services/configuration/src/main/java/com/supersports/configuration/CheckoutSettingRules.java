package com.supersports.configuration;

final class CheckoutSettingRules {
    private CheckoutSettingRules() {}
    static String normalize(String key,String value){
        if(key==null||value==null)throw new IllegalArgumentException("Setting key and value are required");
        String normalized=value.trim();long number;
        try{number=Long.parseLong(normalized);}catch(NumberFormatException e){number=-1;}
        return switch(key){
            case "tax.rate-bps" -> {if(number<0||number>10000)throw new IllegalArgumentException("Tax rate must be from 0 to 10000 basis points");yield Long.toString(number);}
            case "shipping.INR","shipping.USD" -> {if(number<0||number>100000000)throw new IllegalArgumentException("Shipping amount is outside the supported range");yield Long.toString(number);}
            case "inventory.reservation-seconds" -> {if(number<60||number>1800)throw new IllegalArgumentException("Reservation duration must be from 60 to 1800 seconds");yield Long.toString(number);}
            case "payment.authorization-mode" -> {if(!normalized.equals("APPROVE")&&!normalized.equals("DECLINE"))throw new IllegalArgumentException("Authorization mode must be APPROVE or DECLINE");yield normalized;}
            case "returns.window-days" -> {if(number<1||number>90)throw new IllegalArgumentException("Return window must be from 1 to 90 days");yield Long.toString(number);}
            default -> throw new IllegalArgumentException("This setting is not operator-editable");
        };
    }
}
