package com.supersports.reviews;

import java.nio.charset.StandardCharsets;
import java.util.*;

final class DemoReviews {
 private DemoReviews() {}
 static List<UUID> products(List<UUID> products) {
  if(products==null||products.isEmpty()||products.size()>100||products.stream().anyMatch(Objects::isNull)||new HashSet<>(products).size()!=products.size())
   throw new IllegalArgumentException("Provide 1–100 unique product UUIDs");
  return products.stream().sorted().toList();
 }
 static UUID id(UUID product,int slot) {
  return UUID.nameUUIDFromBytes(("supersports:demo-review:v1:"+product+":"+slot).getBytes(StandardCharsets.UTF_8));
 }
 static int rating(int slot) {return 3+slot%3;}
 static String title(int slot) {return List.of("Demo: practice use","Demo: everyday training","Demo: match preparation","Demo: regular sessions").get(slot);}
 static String body(int slot) {return List.of("Synthetic demonstration review for practice sessions.","Synthetic demonstration review for everyday training.","Synthetic demonstration review for match preparation.","Synthetic demonstration review for regular sessions.").get(slot);}
}
