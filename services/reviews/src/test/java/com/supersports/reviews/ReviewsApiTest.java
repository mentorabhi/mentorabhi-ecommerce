package com.supersports.reviews;

import java.util.*;
import jakarta.servlet.Filter;
import jakarta.servlet.http.HttpServletRequest;
import org.junit.jupiter.api.*;
import org.springframework.context.annotation.*;
import org.springframework.mock.web.MockServletContext;
import org.springframework.security.authentication.AuthenticationManagerResolver;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.context.support.AnnotationConfigWebApplicationContext;
import org.springframework.web.servlet.config.annotation.EnableWebMvc;
import org.springframework.http.MediaType;
import static org.mockito.Mockito.*;
import static org.mockito.ArgumentMatchers.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

class ReviewsApiTest {
 AnnotationConfigWebApplicationContext context;MockMvc mvc;ReviewsRepository repo;
 static final UUID PRODUCT=UUID.fromString("11111111-1111-1111-1111-111111111111");
 static final String SEED="{\"operationId\":\"22222222-2222-2222-2222-222222222222\",\"productIds\":[\""+PRODUCT+"\"],\"reviewsPerProduct\":3}";
 @BeforeEach void start(){context=new AnnotationConfigWebApplicationContext();context.setServletContext(new MockServletContext());context.register(Config.class);context.refresh();repo=context.getBean(ReviewsRepository.class);mvc=MockMvcBuilders.webAppContextSetup(context).addFilters(context.getBean("springSecurityFilterChain",Filter.class)).build();}
 @AfterEach void close(){context.close();}
 @Test void summaryIsPublicWithTypedUuidValidationAndBounds()throws Exception{
  when(repo.summaries(List.of(PRODUCT))).thenReturn(List.of(Map.of("productId",PRODUCT,"mean",4.0,"count",3,"histogram",Map.of("1",0,"2",0,"3",1,"4",1,"5",1))));
  mvc.perform(get("/api/v1/reviews/products/summaries").param("productIds",PRODUCT.toString())).andExpect(status().isOk()).andExpect(jsonPath("$[0].count").value(3));
  mvc.perform(get("/api/v1/reviews/products/summaries")).andExpect(status().isBadRequest());
  mvc.perform(get("/api/v1/reviews/products/summaries").param("productIds","invalid")).andExpect(status().isBadRequest());
  mvc.perform(get("/api/v1/reviews/products/summaries").param("productIds",PRODUCT+","+PRODUCT)).andExpect(status().isUnprocessableEntity());
 }
 @Test void publicReviewJsonContainsBadgesWithoutOwnerOrOrderIds()throws Exception{
  when(repo.published(PRODUCT)).thenReturn(List.of(
   Map.of("reviewId",UUID.randomUUID(),"rating",3,"title","Demo","body","Synthetic","createdAt","2026-10-25T00:00:00Z","origin","DEMO","verifiedDelivered",false),
   Map.of("reviewId",UUID.randomUUID(),"rating",5,"title","Good","body","Practice","createdAt","2026-10-25T00:00:00Z","origin","CUSTOMER","verifiedDelivered",true)));
  mvc.perform(get("/api/v1/reviews/products/"+PRODUCT)).andExpect(status().isOk())
   .andExpect(jsonPath("$[0].origin").value("DEMO")).andExpect(jsonPath("$[0].verifiedDelivered").value(false))
   .andExpect(jsonPath("$[1].verifiedDelivered").value(true)).andExpect(jsonPath("$[*].customerSubject").isEmpty())
   .andExpect(jsonPath("$[*].orderId").isEmpty()).andExpect(jsonPath("$[*].skuId").isEmpty());
 }
 @Test void seedRequiresOperatorAudienceAndReturnsConflicts()throws Exception{
  mvc.perform(post("/api/v1/operator/reviews/demo-seed").contentType(MediaType.APPLICATION_JSON).content(SEED)).andExpect(status().isUnauthorized());
  mvc.perform(post("/api/v1/operator/reviews/demo-seed").header("Authorization","Bearer customer").contentType(MediaType.APPLICATION_JSON).content(SEED)).andExpect(status().isForbidden());
  verifyNoInteractions(repo);
  when(repo.seed(any(),eq("operator"),eq(List.of(PRODUCT)),eq(3))).thenReturn(Map.of("replayed",false,"createdCount",3));
  mvc.perform(post("/api/v1/operator/reviews/demo-seed").header("Authorization","Bearer operator").contentType(MediaType.APPLICATION_JSON).content(SEED)).andExpect(status().isOk()).andExpect(jsonPath("$.createdCount").value(3));
  when(repo.seed(any(),eq("operator"),eq(List.of(PRODUCT)),eq(3))).thenThrow(new IllegalStateException("Demo seed operation conflicts"));
  mvc.perform(post("/api/v1/operator/reviews/demo-seed").header("Authorization","Bearer operator").contentType(MediaType.APPLICATION_JSON).content(SEED)).andExpect(status().isConflict());
 }
 @Test void operatorCanFilterModerationStatesButCustomersCannotBrowseQueue()throws Exception{
  mvc.perform(get("/api/v1/operator/reviews").header("Authorization","Bearer customer")).andExpect(status().isForbidden());
  mvc.perform(get("/api/v1/operator/reviews").param("state","PUBLISHED").header("Authorization","Bearer operator")).andExpect(status().isOk());
  mvc.perform(get("/api/v1/operator/reviews").param("state","INVALID").header("Authorization","Bearer operator")).andExpect(status().isUnprocessableEntity());
 }
 @Test void customerSubmissionStaysPendingAndRequiresDeliveredProductProof()throws Exception{
  // The existing real HTTP Orders proof test covers mismatched products; this checks the successful boundary.
  var server=com.sun.net.httpserver.HttpServer.create(new java.net.InetSocketAddress("127.0.0.1",0),0);
  server.createContext("/",exchange->{byte[] body=("{\"verified\":true,\"productId\":\""+PRODUCT+"\"}").getBytes(java.nio.charset.StandardCharsets.UTF_8);exchange.getResponseHeaders().add("Content-Type","application/json");exchange.sendResponseHeaders(200,body.length);exchange.getResponseBody().write(body);exchange.close();});server.start();
  try{
   var controller=new ReviewsController(repo,"http://127.0.0.1:"+server.getAddress().getPort());
   UUID order=UUID.randomUUID(),sku=UUID.randomUUID();
   when(repo.submit(any(),eq("owner"),eq(order),eq(PRODUCT),eq(sku),eq(5),eq("Good"),eq("Practice"))).thenReturn(Map.of("state","PENDING"));
   var jwt=Jwt.withTokenValue("owner-token").header("alg","none").subject("owner").build();
   org.assertj.core.api.Assertions.assertThat(controller.submit(new ReviewsController.ReviewRequest(order,PRODUCT,sku,5,"Good","Practice"),jwt).getBody()).containsEntry("state","PENDING");
   verify(repo).submit(any(),eq("owner"),eq(order),eq(PRODUCT),eq(sku),eq(5),eq("Good"),eq("Practice"));
  }finally{server.stop(0);}
 }
 @Configuration(proxyBeanMethods=false) @EnableWebSecurity @EnableWebMvc @Import(ReviewsSecurity.class)
 static class Config {
  @Bean ReviewsRepository repository(){return mock(ReviewsRepository.class);}
  @Bean ReviewsController controller(ReviewsRepository repo){return new ReviewsController(repo,"http://unused.invalid");}
  @Bean @Primary AuthenticationManagerResolver<HttpServletRequest> testResolver(){return request->authentication->{String value=((org.springframework.security.oauth2.server.resource.authentication.BearerTokenAuthenticationToken)authentication).getToken();String audience="operator".equals(value)?"supersports-api":"supersports-customer-api";return new JwtAuthenticationToken(Jwt.withTokenValue(value).header("alg","none").subject(value).claim("aud",List.of(audience)).build());};}
 }
}
