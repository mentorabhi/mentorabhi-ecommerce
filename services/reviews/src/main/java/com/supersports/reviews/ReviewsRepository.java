package com.supersports.reviews;
import java.util.*;import org.springframework.jdbc.core.JdbcTemplate;import org.springframework.stereotype.Repository;import org.springframework.transaction.annotation.Transactional;
@Repository class ReviewsRepository{
 private final JdbcTemplate jdbc;ReviewsRepository(JdbcTemplate jdbc){this.jdbc=jdbc;}
 @Transactional Map<String,Object> submit(UUID id,String subject,UUID order,UUID product,UUID sku,int rating,String title,String body){ReviewRules.validate(rating,title,body);jdbc.query("SELECT pg_advisory_xact_lock(hashtextextended(?,0))",ps->ps.setString(1,"verified-review:"+subject+":"+order+":"+sku),rs->{rs.next();return null;});var old=jdbc.queryForList("SELECT id,state FROM product_review WHERE customer_subject=? AND order_id=? AND sku_id=?",subject,order,sku);if(!old.isEmpty())throw new IllegalStateException("A review already exists for this purchase");jdbc.update("INSERT INTO product_review(id,customer_subject,order_id,product_id,sku_id,rating,title,body) VALUES (?,?,?,?,?,?,?,?)",id,subject,order,product,sku,rating,title.trim(),body.trim());return Map.of("reviewId",id,"state","PENDING");}
 List<Map<String,Object>> mine(String subject){return jdbc.queryForList("SELECT id AS \"reviewId\",order_id AS \"orderId\",product_id AS \"productId\",sku_id AS \"skuId\",rating,title,body,state,created_at AS \"createdAt\" FROM product_review WHERE customer_subject=? ORDER BY created_at DESC",subject);}
 List<Map<String,Object>> published(UUID product){return jdbc.queryForList("SELECT id AS \"reviewId\",rating,title,body,created_at AS \"createdAt\",origin,(origin='CUSTOMER') AS \"verifiedDelivered\" FROM product_review WHERE product_id=? AND state='PUBLISHED' ORDER BY created_at DESC LIMIT 100",product);}
 List<Map<String,Object>> summaries(List<UUID> products){
  var ids=DemoReviews.products(products);
  var rows=jdbc.queryForList("SELECT product_id,rating,count(*) AS total FROM product_review WHERE state='PUBLISHED' AND product_id IN ("+String.join(",",Collections.nCopies(ids.size(),"?"))+") GROUP BY product_id,rating",ids.toArray());
  List<Map<String,Object>> result=new ArrayList<>();
  for(var product:ids){
   Map<String,Long> histogram=new LinkedHashMap<>();for(int rating=1;rating<=5;rating++)histogram.put(String.valueOf(rating),0L);
   long count=0,sum=0;
   for(var row:rows)if(product.equals(row.get("product_id"))){int rating=((Number)row.get("rating")).intValue();long total=((Number)row.get("total")).longValue();histogram.put(String.valueOf(rating),total);count+=total;sum+=rating*total;}
   Map<String,Object> summary=new LinkedHashMap<>();summary.put("productId",product);summary.put("mean",count==0?null:java.math.BigDecimal.valueOf(sum).divide(java.math.BigDecimal.valueOf(count),2,java.math.RoundingMode.HALF_UP));summary.put("count",count);summary.put("histogram",histogram);result.add(summary);
  }
  return result;
 }
 @Transactional Map<String,Object> seed(UUID operation,String actor,List<UUID> products,int count){
  var ids=DemoReviews.products(products);
  if(operation==null||actor==null||actor.isBlank()||(count!=3&&count!=4))throw new IllegalArgumentException("Invalid demo seed");
  String identity=ids.stream().map(UUID::toString).collect(java.util.stream.Collectors.joining(","));
  jdbc.query("SELECT pg_advisory_xact_lock(hashtextextended(?,0))",ps->ps.setString(1,"review-demo-seed:"+operation),rs->{rs.next();return null;});
  var prior=jdbc.queryForList("SELECT actor_subject,product_ids,reviews_per_product,created_count FROM review_demo_seed_operation WHERE operation_id=?",operation);
  if(!prior.isEmpty()){
   var row=prior.getFirst();
   if(!actor.equals(row.get("actor_subject"))||!identity.equals(row.get("product_ids"))||count!=((Number)row.get("reviews_per_product")).intValue())throw new IllegalStateException("Demo seed operation conflicts");
   return Map.of("operationId",operation,"productCount",ids.size(),"reviewsPerProduct",count,"createdCount",row.get("created_count"),"replayed",true);
  }
  int created=0;
  for(var product:ids)for(int slot=0;slot<count;slot++){
   UUID id=DemoReviews.id(product,slot);
   created+=jdbc.update("INSERT INTO product_review(id,product_id,rating,title,body,origin,state) VALUES (?,?,?,?,?,'DEMO','PUBLISHED') ON CONFLICT (id) DO NOTHING",id,product,DemoReviews.rating(slot),DemoReviews.title(slot),DemoReviews.body(slot));
   var row=jdbc.queryForMap("SELECT origin,product_id,rating,title,body FROM product_review WHERE id=?",id);
   if(!"DEMO".equals(row.get("origin"))||!product.equals(row.get("product_id"))||DemoReviews.rating(slot)!=((Number)row.get("rating")).intValue()||!DemoReviews.title(slot).equals(row.get("title"))||!DemoReviews.body(slot).equals(row.get("body")))throw new IllegalStateException("Demo review identity conflicts");
  }
  jdbc.update("INSERT INTO review_demo_seed_operation(operation_id,actor_subject,product_ids,reviews_per_product,created_count) VALUES (?,?,?,?,?)",operation,actor,identity,count,created);
  return Map.of("operationId",operation,"productCount",ids.size(),"reviewsPerProduct",count,"createdCount",created,"replayed",false);
 }
 List<Map<String,Object>> queue(){return jdbc.queryForList("SELECT id AS \"reviewId\",order_id AS \"orderId\",product_id AS \"productId\",sku_id AS \"skuId\",rating,title,body,state,created_at AS \"createdAt\" FROM product_review WHERE state='PENDING' ORDER BY created_at,id LIMIT 200");}
 List<Map<String,Object>> moderationRows(String state,UUID product){return jdbc.queryForList("SELECT id AS \"reviewId\",order_id AS \"orderId\",product_id AS \"productId\",sku_id AS \"skuId\",rating,title,body,state,origin,created_at AS \"createdAt\" FROM product_review WHERE state=? AND (?::uuid IS NULL OR product_id=?) ORDER BY created_at DESC,id LIMIT 200",state,product,product);}
 @Transactional Map<String,Object> moderate(UUID id,String target,String actor,String reason,UUID operation){ReviewRules.moderate(target,reason);jdbc.query("SELECT pg_advisory_xact_lock(hashtextextended(?,0))",ps->ps.setString(1,"review-moderation:"+operation),rs->{rs.next();return null;});var prior=jdbc.queryForList("SELECT review_id,next_state,actor_subject,reason FROM review_moderation_audit WHERE operation_id=?",operation);if(!prior.isEmpty()){var row=prior.getFirst();if(!id.equals(row.get("review_id"))||!target.equals(row.get("next_state"))||!actor.equals(row.get("actor_subject"))||!reason.trim().equals(row.get("reason")))throw new IllegalStateException("Moderation operation conflicts");return Map.of("reviewId",id,"state",target,"replayed",true);}var rows=jdbc.queryForList("SELECT state FROM product_review WHERE id=? FOR UPDATE",id);if(rows.isEmpty())throw new NoSuchElementException("Review not found");String old=rows.getFirst().get("state").toString();if(!old.equals("PENDING")&&!target.equals("HIDDEN"))throw new IllegalStateException("Only pending reviews can be decided");jdbc.update("UPDATE product_review SET state=?,revision=revision+1,updated_at=now() WHERE id=?",target,id);jdbc.update("INSERT INTO review_moderation_audit(operation_id,review_id,actor_subject,previous_state,next_state,reason) VALUES (?,?,?,?,?,?)",operation,id,actor,old,target,reason.trim());return Map.of("reviewId",id,"state",target,"replayed",false);}
}
