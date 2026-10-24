package com.supersports.reviews;
final class ReviewRules{
 private ReviewRules(){}
 static void validate(int rating,String title,String body){if(rating<1||rating>5||title==null||title.isBlank()||title.trim().length()>120||body==null||body.isBlank()||body.trim().length()>2000)throw new IllegalArgumentException("Review needs a 1–5 rating, title and body within limits");}
 static void moderate(String state,String reason){if(!java.util.Set.of("PUBLISHED","REJECTED","HIDDEN").contains(state)||reason==null||reason.isBlank()||reason.trim().length()>500)throw new IllegalArgumentException("Invalid moderation decision");}
}
