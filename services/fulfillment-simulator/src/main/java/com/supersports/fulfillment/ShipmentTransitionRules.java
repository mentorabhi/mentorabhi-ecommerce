package com.supersports.fulfillment;

import java.util.Map;

final class ShipmentTransitionRules {
    private static final Map<String,String> NEXT=Map.of(
        "SCHEDULED","HANDED_OFF", "HANDED_OFF","IN_TRANSIT", "IN_TRANSIT","DELIVERED");
    private ShipmentTransitionRules(){}

    static boolean permits(String current,String requested){return requested!=null&&requested.equals(NEXT.get(current));}
}
