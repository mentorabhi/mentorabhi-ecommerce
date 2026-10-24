package com.supersports.reviews;
import static org.junit.jupiter.api.Assertions.*;import org.junit.jupiter.api.Test;
class ReviewRulesTest{
 @Test void boundsCustomerReview(){ReviewRules.validate(5,"Solid bat","Good balance and finish.");assertThrows(IllegalArgumentException.class,()->ReviewRules.validate(0,"x","y"));assertThrows(IllegalArgumentException.class,()->ReviewRules.validate(4," ","body"));}
 @Test void onlyAllowsAuditedModerationStates(){ReviewRules.moderate("PUBLISHED","Meets guidelines");assertThrows(IllegalArgumentException.class,()->ReviewRules.moderate("PENDING","reason"));assertThrows(IllegalArgumentException.class,()->ReviewRules.moderate("HIDDEN"," "));}
}
