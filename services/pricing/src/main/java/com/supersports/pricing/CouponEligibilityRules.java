package com.supersports.pricing;
import java.util.List;
import java.util.Map;

final class CouponEligibilityRules {
    private CouponEligibilityRules() {}
    static boolean eligible(String categorySlug,Map<String,Object> rules){
        Object raw=rules==null?null:rules.get("categorySlugs");
        if(raw==null)return true;
        if(!(raw instanceof List<?> categories)||categories.isEmpty())return false;
        return categories.stream().anyMatch(value->categorySlug.equals(value));
    }
}
