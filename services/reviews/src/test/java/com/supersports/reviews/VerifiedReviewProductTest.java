package com.supersports.reviews;
import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;
import com.sun.net.httpserver.HttpServer;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.server.ResponseStatusException;

class VerifiedReviewProductTest {
 @Test void deliveredSkuCannotVerifyAReviewForAnotherProduct() throws Exception {
  UUID product=UUID.randomUUID();
  var server=HttpServer.create(new InetSocketAddress("127.0.0.1",0),0);
  server.createContext("/",exchange->{byte[] body=("{\"verified\":true,\"productId\":\""+product+"\"}").getBytes(StandardCharsets.UTF_8);exchange.getResponseHeaders().add("Content-Type","application/json");exchange.sendResponseHeaders(200,body.length);exchange.getResponseBody().write(body);exchange.close();});
  server.start();
  try {
   var repository=mock(ReviewsRepository.class);
   var controller=new ReviewsController(repository,"http://127.0.0.1:"+server.getAddress().getPort());
   var jwt=Jwt.withTokenValue("test").header("alg","none").subject("customer").build();
   var request=new ReviewsController.ReviewRequest(UUID.randomUUID(),UUID.randomUUID(),UUID.randomUUID(),5,"Nice kit","Used for local practice.");
   assertThatThrownBy(()->controller.submit(request,jwt)).isInstanceOfSatisfying(ResponseStatusException.class,error->assertThat(error.getStatusCode().value()).isEqualTo(422));
   verifyNoInteractions(repository);
  } finally {server.stop(0);}
 }
}
