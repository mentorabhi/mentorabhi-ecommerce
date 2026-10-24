package com.supersports.orderhistory;
import java.util.Map;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.boot.autoconfigure.condition.ConditionalOnWebApplication;
@RestController @RequestMapping("/api/v1/order-history") @ConditionalOnWebApplication(type=ConditionalOnWebApplication.Type.SERVLET)
class HistoryController {
 private final HistoryProjector projector;private final CustomerKey ownerKey;private final ProjectionFreshness freshness;
 HistoryController(HistoryProjector projector,CustomerKey ownerKey,ProjectionFreshness freshness){this.projector=projector;this.ownerKey=ownerKey;this.freshness=freshness;}
 @GetMapping ResponseEntity<?> list(@AuthenticationPrincipal Jwt jwt,@RequestParam Map<String,String> query){if(query.containsKey("customerSubject")||query.containsKey("customerKey")||query.containsKey("owner"))return ResponseEntity.badRequest().body(Map.of("code","OWNER_FILTER_NOT_ALLOWED"));String key=ownerKey.forSubject(jwt.getSubject());return ResponseEntity.ok(Map.of("orders",projector.list(key),"freshness",freshness.view(projector.ownedGap(key))));}
 @GetMapping("/{orderId}") ResponseEntity<?> get(@AuthenticationPrincipal Jwt jwt,@PathVariable UUID orderId){var result=projector.get(orderId,ownerKey.forSubject(jwt.getSubject()));return result==null?ResponseEntity.status(HttpStatus.NOT_FOUND).body(Map.of("code","ORDER_NOT_FOUND")):ResponseEntity.ok(result);}
}
