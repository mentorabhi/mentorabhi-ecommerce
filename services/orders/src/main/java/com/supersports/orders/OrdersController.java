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
    @GetMapping("/{orderId}") Map<String,Object> order(@PathVariable UUID orderId,@AuthenticationPrincipal Jwt jwt){var result=repository.order(orderId,jwt.getSubject());if(result==null)throw new ResponseStatusException(HttpStatus.NOT_FOUND);return result;}
}
