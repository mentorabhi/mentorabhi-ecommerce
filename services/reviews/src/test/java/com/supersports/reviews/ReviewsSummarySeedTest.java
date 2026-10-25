package com.supersports.reviews;

import java.util.*;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.jdbc.core.JdbcTemplate;
import static org.assertj.core.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class ReviewsSummarySeedTest {
 final JdbcTemplate jdbc=mock(JdbcTemplate.class);
 final ReviewsRepository repo=new ReviewsRepository(jdbc);
 final UUID product=UUID.fromString("11111111-1111-1111-1111-111111111111");
 final UUID operation=UUID.randomUUID();

 @Test void summaryUsesPublishedRowsOnlyAndIncludesEmptyProductsAndAllBuckets(){
  UUID empty=UUID.randomUUID();
  when(jdbc.queryForList(anyString(),any(Object[].class))).thenReturn(List.of(
   Map.of("product_id",product,"rating",3,"total",2L),Map.of("product_id",product,"rating",5,"total",1L)));
  var rows=repo.summaries(List.of(product,empty));
  var rated=rows.stream().filter(r->product.equals(r.get("productId"))).findFirst().orElseThrow();
  assertThat(rated.get("mean")).isEqualTo(new java.math.BigDecimal("3.67"));
  assertThat(rated.get("count")).isEqualTo(3L);
  assertThat(rated.get("histogram")).isEqualTo(Map.of("1",0L,"2",0L,"3",2L,"4",0L,"5",1L));
  var zero=rows.stream().filter(r->empty.equals(r.get("productId"))).findFirst().orElseThrow();
  assertThat(zero.get("mean")).isNull();assertThat(zero.get("count")).isEqualTo(0L);
  var sql=ArgumentCaptor.forClass(String.class);verify(jdbc).queryForList(sql.capture(),any(Object[].class));
  assertThat(sql.getValue()).contains("state='PUBLISHED'","IN (?,?)","GROUP BY product_id,rating").doesNotContain("LIMIT","origin=");
 }
 @Test void batchBoundsRejectNullDuplicateAndOver100ButAllow100(){
  assertThatThrownBy(()->repo.summaries(null)).isInstanceOf(IllegalArgumentException.class);
  assertThatThrownBy(()->repo.summaries(List.of())).isInstanceOf(IllegalArgumentException.class);
  assertThatThrownBy(()->repo.summaries(List.of(product,product))).isInstanceOf(IllegalArgumentException.class);
  assertThatThrownBy(()->repo.summaries(Arrays.asList(product,null))).isInstanceOf(IllegalArgumentException.class);
  var ids=java.util.stream.IntStream.range(0,101).mapToObj(i->UUID.randomUUID()).toList();
  assertThatThrownBy(()->repo.summaries(ids)).isInstanceOf(IllegalArgumentException.class);
  assertThat(repo.summaries(ids.subList(0,100))).hasSize(100);
 }
 @Test void publicProjectionExcludesPrivatePurchaseFieldsAndLabelsOrigin(){
  repo.published(product);
  var sql=ArgumentCaptor.forClass(String.class);verify(jdbc).queryForList(sql.capture(),eq(product));
  assertThat(sql.getValue()).contains("origin", "(origin='CUSTOMER') AS \"verifiedDelivered\"","state='PUBLISHED'")
   .doesNotContain("customer_subject","order_id","sku_id","SELECT *");
 }
 @Test void deterministicRowsArePublishedDemoWithoutPurchaseIdentity(){
  when(jdbc.update(anyString(),any(Object[].class))).thenReturn(1);
  when(jdbc.queryForMap(anyString(),any(Object[].class))).thenAnswer(call->{
   UUID id=call.getArgument(1);int slot=java.util.stream.IntStream.range(0,4).filter(i->DemoReviews.id(product,i).equals(id)).findFirst().orElseThrow();
   return Map.of("origin","DEMO","product_id",product,"rating",DemoReviews.rating(slot),"title",DemoReviews.title(slot),"body",DemoReviews.body(slot));
  });
  var response=repo.seed(operation,"operator",List.of(product),4);
  assertThat(response).containsEntry("createdCount",4).containsEntry("replayed",false);
  for(int i=0;i<4;i++){
   assertThat(DemoReviews.rating(i)).isBetween(3,5);
   verify(jdbc).update("INSERT INTO product_review(id,product_id,rating,title,body,origin,state) VALUES (?,?,?,?,?,'DEMO','PUBLISHED') ON CONFLICT (id) DO NOTHING",DemoReviews.id(product,i),product,DemoReviews.rating(i),DemoReviews.title(i),DemoReviews.body(i));
  }
 }
 void prior(String actor,String products,int count){
  when(jdbc.queryForList(contains("review_demo_seed_operation"),eq(operation)))
   .thenReturn(List.of(Map.of("actor_subject",actor,"product_ids",products,"reviews_per_product",count,"created_count",3)));
 }
 @Test void replayReturnsOriginalReceiptWithoutAnyWrites(){
  prior("operator",product.toString(),3);
  assertThat(repo.seed(operation,"operator",List.of(product),3)).containsEntry("replayed",true).containsEntry("createdCount",3);
  verify(jdbc,never()).update(anyString(),any(Object[].class));
 }
 @Test void sameOperationChangedActorProductsOrCountConflicts(){
  prior("operator",product.toString(),3);
  assertThatThrownBy(()->repo.seed(operation,"other",List.of(product),3)).isInstanceOf(IllegalStateException.class);
  assertThatThrownBy(()->repo.seed(operation,"operator",List.of(UUID.randomUUID()),3)).isInstanceOf(IllegalStateException.class);
  assertThatThrownBy(()->repo.seed(operation,"operator",List.of(product),4)).isInstanceOf(IllegalStateException.class);
  verify(jdbc,never()).update(anyString(),any(Object[].class));
 }
 @Test void productOrderIsCanonicalAndStableAcrossOperationIds(){
  UUID second=UUID.randomUUID();var ids=DemoReviews.products(List.of(product,second));
  String identity=ids.stream().map(UUID::toString).collect(java.util.stream.Collectors.joining(","));
  prior("operator",identity,3);
  assertThat(repo.seed(operation,"operator",List.of(second,product),3)).containsEntry("replayed",true);
  assertThat(DemoReviews.id(product,0)).isEqualTo(DemoReviews.id(product,0)).isNotEqualTo(DemoReviews.id(product,1));
 }
 @Test void newOperationDoesNotReinsertOrRepublishExistingDemoRows(){
  when(jdbc.queryForMap(anyString(),any(Object[].class))).thenAnswer(call->{
   UUID id=call.getArgument(1);int slot=java.util.stream.IntStream.range(0,3).filter(i->DemoReviews.id(product,i).equals(id)).findFirst().orElseThrow();
   return Map.of("origin","DEMO","product_id",product,"rating",DemoReviews.rating(slot),"title",DemoReviews.title(slot),"body",DemoReviews.body(slot));
  });
  assertThat(repo.seed(operation,"operator",List.of(product),3)).containsEntry("createdCount",0);
  verify(jdbc,never()).update(startsWith("UPDATE"),any(Object[].class));
 }
 @Test void occupiedIdentityWithDifferentPayloadConflicts(){
  when(jdbc.queryForMap(anyString(),any(Object[].class))).thenReturn(Map.of("origin","CUSTOMER"));
  assertThatThrownBy(()->repo.seed(operation,"operator",List.of(product),3)).isInstanceOf(IllegalStateException.class);
 }
 @Test void seedRejectsInvalidCountAndMissingIdentityBeforeDatabaseWork(){
  for(int count:new int[]{0,2,5})assertThatThrownBy(()->repo.seed(operation,"operator",List.of(product),count)).isInstanceOf(IllegalArgumentException.class);
  assertThatThrownBy(()->repo.seed(null,"operator",List.of(product),3)).isInstanceOf(IllegalArgumentException.class);
  verifyNoInteractions(jdbc);
 }
}
