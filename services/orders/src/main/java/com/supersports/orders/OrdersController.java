package com.supersports.orders;
import java.util.Map;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.web.client.RestClientException;

@RestController @RequestMapping("/api/v1/orders")
class OrdersController {
    private final OrdersRepository repository;
    private final CheckoutValidationService validation;
    private final CheckoutSagaWorker fulfillment;
    OrdersController(OrdersRepository repository,CheckoutValidationService validation,CheckoutSagaWorker fulfillment){this.repository=repository;this.validation=validation;this.fulfillment=fulfillment;}
    @PostMapping("/checkout") ResponseEntity<Map<String,Object>> checkout(@RequestHeader(value="Idempotency-Key",required=false)String key,@RequestBody CheckoutRules.CheckoutInput input,@AuthenticationPrincipal Jwt jwt){
        try{CheckoutRules.validateKey(key);var lines=CheckoutRules.normalize(input.lines());String hash=CheckoutRules.payloadHash(lines,input.couponCode());var result=repository.claim(jwt.getSubject(),key,hash,lines,input.couponCode());if(Boolean.TRUE.equals(result.get("conflict")))throw new ResponseStatusException(HttpStatus.CONFLICT,"Idempotency key was used with different checkout details");
            if("REJECTED".equals(result.get("status")))throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,"This checkout request was previously rejected: "+result.get("errorCode"));
            if("ACCEPTED".equals(result.get("status"))||Boolean.TRUE.equals(result.get("replayed"))&&!Boolean.TRUE.equals(result.get("resumeValidation")))return ResponseEntity.accepted().body(result);
            try{return ResponseEntity.accepted().body(validation.validate(UUID.fromString(result.get("requestId").toString()),jwt.getSubject(),jwt.getTokenValue(),lines,input.couponCode()));}
            catch(CheckoutValidationService.CheckoutRejectedException e){repository.reject(UUID.fromString(result.get("requestId").toString()),e.getMessage());throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,e.getMessage());}
            catch(org.springframework.web.client.HttpClientErrorException e){if(e.getStatusCode().value()==422||e.getStatusCode().value()==404){repository.reject(UUID.fromString(result.get("requestId").toString()),"CHECKOUT_VALIDATION_REJECTED");throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,"Checkout could not be validated");}throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE,"Checkout validation service unavailable");}
            catch(org.springframework.web.client.RestClientException|IllegalStateException e){throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE,"Checkout validation service unavailable");}
        }
        catch(IllegalArgumentException e){throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,e.getMessage());}
    }
    @GetMapping("/checkout-requests/{requestId}") Map<String,Object> request(@PathVariable UUID requestId,@AuthenticationPrincipal Jwt jwt){var result=repository.request(requestId,jwt.getSubject());if(result==null)throw new ResponseStatusException(HttpStatus.NOT_FOUND);return result;}
    @GetMapping List<Map<String,Object>> orders(@AuthenticationPrincipal Jwt jwt){return repository.orders(jwt.getSubject());}
    @GetMapping("/{orderId}/tracking") Map<String,Object> tracking(@PathVariable UUID orderId,@AuthenticationPrincipal Jwt jwt){
        if(!repository.ownsOrder(orderId,jwt.getSubject()))throw new ResponseStatusException(HttpStatus.NOT_FOUND);
        Map<String,Object> shipment;
        try{shipment=fulfillment.fulfillmentStatus(orderId);if(shipment==null)shipment=Map.of("state","UNAVAILABLE");}
        catch(RestClientException error){shipment=Map.of("state","UNAVAILABLE");}
        return Map.of("orderId",orderId,"tracking",shipment);
    }
    @GetMapping("/{orderId}/cancellation-eligibility") Map<String,Object> cancellationEligibility(@PathVariable UUID orderId,@AuthenticationPrincipal Jwt jwt){
        var eligibility=repository.cancellationEligibility(orderId,jwt.getSubject());if(eligibility==null)throw new ResponseStatusException(HttpStatus.NOT_FOUND);
        if(!"FULFILLMENT_SCHEDULED".equals(eligibility.get("orderState")))return Map.of("eligible",false,"reasonCode","ORDER_NOT_CANCELLABLE");
        try{var tracking=fulfillment.fulfillmentStatus(orderId);boolean eligible=tracking!=null&&PostPurchaseCancellationRules.eligible(eligibility.get("orderState").toString(),tracking.get("state").toString());
            var response=new java.util.LinkedHashMap<String,Object>();response.put("eligible",eligible);response.put("reasonCode",eligible?"ELIGIBLE":"HANDOFF_OR_FULFILLMENT_STARTED");response.put("shipmentRevision",tracking==null?null:tracking.get("revision"));return response;
        }catch(RestClientException failure){throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE,"Fulfillment status is unavailable");}
    }
    @PostMapping("/{orderId}/cancellations") ResponseEntity<Map<String,Object>> cancel(@PathVariable UUID orderId,@RequestHeader("Idempotency-Key")String key,@RequestBody CancellationRequest request,@AuthenticationPrincipal Jwt jwt){
        if(key.isBlank()||key.length()>120||request==null)throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,"Invalid cancellation request");
        try{PostPurchaseCancellationRules.requireCustomerReason(request.reasonCode());}catch(IllegalArgumentException invalid){throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,"Invalid cancellation reason");}
        var owned=repository.cancellationEligibility(orderId,jwt.getSubject());if(owned==null)throw new ResponseStatusException(HttpStatus.NOT_FOUND);
        if(!"FULFILLMENT_SCHEDULED".equals(owned.get("orderState")))throw new ResponseStatusException(HttpStatus.CONFLICT,"Order is not eligible for cancellation");
        try{var shipment=fulfillment.fulfillmentStatus(orderId);if(shipment==null||!"SCHEDULED".equals(shipment.get("state")))throw new ResponseStatusException(HttpStatus.CONFLICT,"Shipment handoff already started");
            String hash=java.util.HexFormat.of().formatHex(java.security.MessageDigest.getInstance("SHA-256").digest(request.reasonCode().getBytes(java.nio.charset.StandardCharsets.UTF_8)));
            var result=repository.startCancellation(orderId,jwt.getSubject(),key,hash,((Number)shipment.get("revision")).longValue());
            if(result==null)throw new ResponseStatusException(HttpStatus.NOT_FOUND);
            return ResponseEntity.accepted().body(Map.of("orderId",orderId,"operationId",result.get("operation_id"),"status",result.get("status"),"currentStep",result.get("current_step")));
        }catch(RestClientException failure){throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE,"Fulfillment status is unavailable");}
        catch(java.security.NoSuchAlgorithmException impossible){throw new IllegalStateException(impossible);}
        catch(IllegalStateException conflict){throw new ResponseStatusException(HttpStatus.CONFLICT,conflict.getMessage());}
    }
    @GetMapping("/{orderId}/cancellations/{operationId}") Map<String,Object> cancellation(@PathVariable UUID orderId,@PathVariable UUID operationId,@AuthenticationPrincipal Jwt jwt){var result=repository.cancellation(orderId,operationId,jwt.getSubject());if(result==null)throw new ResponseStatusException(HttpStatus.NOT_FOUND);return result;}
    @GetMapping("/{orderId}") Map<String,Object> order(@PathVariable UUID orderId,@AuthenticationPrincipal Jwt jwt){var result=repository.order(orderId,jwt.getSubject());if(result==null)throw new ResponseStatusException(HttpStatus.NOT_FOUND);return result;}
    record CancellationRequest(String reasonCode){}
}
