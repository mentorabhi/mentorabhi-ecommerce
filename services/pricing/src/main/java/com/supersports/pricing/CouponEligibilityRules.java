package com.supersports.pricing;
import java.util.List;
import java.util.Map;

final class CouponEligibilityRules {
    private CouponEligibilityRules() {}
    static boolean eligible(String productId,String categorySlug,Map<String,Object> rules){
        return matches(productId,rules==null?null:rules.get("productIds"))
            && matches(categorySlug,rules==null?null:rules.get("categorySlugs"));
    }
    private static boolean matches(String candidate,Object raw){
        if(raw==null)return true;
        if(!(raw instanceof List<?> categories)||categories.isEmpty())return false;
        return categories.stream().anyMatch(value->candidate.equals(value));
    }
}
