package com.supersports.inventory;
import java.util.*;import org.springframework.beans.factory.annotation.Value;import org.springframework.http.*;import org.springframework.security.core.annotation.AuthenticationPrincipal;import org.springframework.security.oauth2.jwt.Jwt;import org.springframework.web.bind.annotation.*;import org.springframework.web.client.RestClient;import org.springframework.web.client.RestClientException;import org.springframework.web.server.ResponseStatusException;
@RestController @RequestMapping("/api/v1/inventory") class InventoryController{
 private final InventoryRepository repo;private final RestClient catalog;InventoryController(InventoryRepository repo,@Value("${catalog.base-url}")String catalogUrl){this.repo=repo;catalog=RestClient.builder().baseUrl(catalogUrl).build();}
 @GetMapping("/warehouses") List<Map<String,Object>> warehouses(){return List.of(Map.of("id",InventoryRepository.WAREHOUSE,"name","Main warehouse","active",true));}
 @GetMapping("/availability/{skuId}") Map<String,Object> availability(@PathVariable UUID skuId){return Map.of("skuId",skuId,"available",Math.max(0,repo.availability(skuId)),"reserved",0,"snapshot",true);}
 @GetMapping("/balances") List<Map<String,Object>> balances(){return repo.balances();}
 @GetMapping("/movements") List<Map<String,Object>> movements(@RequestParam(required=false)UUID skuId){return repo.movements(skuId);}
 @GetMapping("/returns/pending") List<Map<String,Object>> pendingReturns(){return repo.pendingReturns();}
 @PostMapping("/returns/{returnId}/inspection") ResponseEntity<Map<String,Object>> inspectReturn(@PathVariable UUID returnId,@RequestBody InspectionRequest request,@AuthenticationPrincipal Jwt jwt){
  if(request==null||request.operationId()==null||request.expectedRevision()<0||request.decisions()==null||request.decisions().stream().anyMatch(java.util.Objects::isNull))throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,"Invalid inspection request");
  try{return ResponseEntity.ok(repo.inspectReturn(returnId,request.expectedRevision(),request.operationId(),jwt.getSubject(),request.decisions().stream().map(decision->new ReturnInspectionRules.Decision(decision.skuId(),decision.ordinal(),decision.condition(),decision.reason())).toList()));}
  catch(InventoryRepository.ReturnNotFoundException missing){throw new ResponseStatusException(HttpStatus.NOT_FOUND,"Return receipt not found");}
  catch(InventoryRepository.ReturnOperationConflictException conflict){throw new ResponseStatusException(HttpStatus.CONFLICT,"Inspection operation conflicts with an earlier request");}
  catch(InventoryRepository.StaleReturnRevisionException stale){throw new ResponseStatusException(HttpStatus.CONFLICT,"Return revision changed");}
  catch(IllegalStateException conflict){throw new ResponseStatusException(HttpStatus.CONFLICT,conflict.getMessage());}
  catch(IllegalArgumentException invalid){throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,"Inspection must cover every received unit");}
 }
 @PostMapping("/adjustments") ResponseEntity<Map<String,Object>> adjust(@RequestBody Adjustment a,@AuthenticationPrincipal Jwt jwt){try{UUID sku=UUID.fromString(a.skuId());var status=catalog.get().uri("/api/v1/catalog/skus/{id}/status",sku).headers(h->h.setBearerAuth(jwt.getTokenValue())).retrieve().body(SkuStatus.class);if(status==null||!status.active())throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,"SKU must be active in Catalog");var result=repo.adjust(sku,a.delta(),jwt.getSubject(),a.reason(),a.idempotencyKey());if(Boolean.TRUE.equals(result.get("conflict")))return ResponseEntity.status(HttpStatus.CONFLICT).body(Map.of("error","Idempotency key was already used with a different request"));return ResponseEntity.ok(result);}catch(RestClientException e){throw new ResponseStatusException(HttpStatus.BAD_GATEWAY,"Catalog validation unavailable");}catch(IllegalArgumentException e){throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,e.getMessage());}}
 record Adjustment(String skuId,long delta,String reason,String idempotencyKey){} record SkuStatus(UUID id,boolean active){}
 record InspectionRequest(long expectedRevision,UUID operationId,List<InspectionDecision> decisions){}
 record InspectionDecision(UUID skuId,int ordinal,String condition,String reason){}
}
