package com.supersports.orders;
import java.util.Map;
import java.util.List;
import java.util.UUID;
import java.time.Instant;
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
        String hash=PostPurchaseCancellationRules.reasonHash(request.reasonCode());
        try{var replay=repository.cancellationReplay(orderId,jwt.getSubject(),key,hash);if(replay!=null)return ResponseEntity.accepted().body(replay);}
        catch(IllegalStateException conflict){throw new ResponseStatusException(HttpStatus.CONFLICT,conflict.getMessage());}
        if(!"FULFILLMENT_SCHEDULED".equals(owned.get("orderState")))throw new ResponseStatusException(HttpStatus.CONFLICT,"Order is not eligible for cancellation");
        try{var shipment=fulfillment.fulfillmentStatus(orderId);if(shipment==null||!"SCHEDULED".equals(shipment.get("state")))throw new ResponseStatusException(HttpStatus.CONFLICT,"Shipment handoff already started");
            var result=repository.startCancellation(orderId,jwt.getSubject(),key,hash,((Number)shipment.get("revision")).longValue());
            if(result==null)throw new ResponseStatusException(HttpStatus.NOT_FOUND);
            return ResponseEntity.accepted().body(Map.of("orderId",orderId,"operationId",result.get("operation_id"),"status",result.get("status"),"currentStep",result.get("current_step")));
        }catch(RestClientException failure){throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE,"Fulfillment status is unavailable");}
        catch(IllegalStateException conflict){throw new ResponseStatusException(HttpStatus.CONFLICT,conflict.getMessage());}
    }
    @GetMapping("/{orderId}/cancellations/{operationId}") Map<String,Object> cancellation(@PathVariable UUID orderId,@PathVariable UUID operationId,@AuthenticationPrincipal Jwt jwt){var result=repository.cancellation(orderId,operationId,jwt.getSubject());if(result==null)throw new ResponseStatusException(HttpStatus.NOT_FOUND);return result;}
    @GetMapping("/{orderId}/returns/eligibility") Map<String,Object> returnEligibility(@PathVariable UUID orderId,@AuthenticationPrincipal Jwt jwt){
        var lines=repository.returnableLines(orderId,jwt.getSubject());if(lines==null)throw new ResponseStatusException(HttpStatus.NOT_FOUND);
        try{var shipment=fulfillment.fulfillmentStatus(orderId);var policy=fulfillment.returnsPolicy();var deliveredAt=deliveredAt(shipment);boolean delivered=shipment!=null&&"DELIVERED".equals(shipment.get("state"));
            boolean inWindow=delivered&&ReturnRequestRules.withinWindow(deliveredAt,java.time.Instant.now(),((Number)policy.get("windowDays")).longValue());
            return Map.of("eligible",inWindow,"reasonCode",!delivered?"NOT_DELIVERED":inWindow?"ELIGIBLE":"RETURN_WINDOW_EXPIRED","windowDays",((Number)policy.get("windowDays")).longValue(),"policyRevision",((Number)policy.get("policyRevision")).longValue(),"returnableLines",lines);
        }catch(RestClientException failure){throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE,"Return eligibility dependencies are unavailable");}
    }
    @PostMapping("/{orderId}/returns") ResponseEntity<Map<String,Object>> requestReturn(@PathVariable UUID orderId,@RequestHeader("Idempotency-Key")String key,@RequestBody ReturnRequest request,@AuthenticationPrincipal Jwt jwt){
        if(key.isBlank()||key.length()>120||request==null)throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,"Invalid return request");
        try{
            var lines=ReturnRequestRules.normalize(request.lines());String hash=ReturnRequestRules.payloadHash(lines);
            var existing=repository.returnReplay(orderId,jwt.getSubject(),key,hash);if(existing!=null)return ResponseEntity.accepted().body(existing);
            if(!repository.ownsOrder(orderId,jwt.getSubject()))throw new ResponseStatusException(HttpStatus.NOT_FOUND);
            var shipment=fulfillment.fulfillmentStatus(orderId);var policy=fulfillment.returnsPolicy();Instant delivered=deliveredAt(shipment);
            if(shipment==null||!"DELIVERED".equals(shipment.get("state"))||!ReturnRequestRules.withinWindow(delivered,Instant.now(),((Number)policy.get("windowDays")).longValue()))throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,"Return is outside the delivered-order policy window");
            var result=repository.startReturn(orderId,jwt.getSubject(),key,hash,lines,delivered,((Number)policy.get("windowDays")).longValue(),((Number)policy.get("policyRevision")).longValue());
            if(result==null)throw new ResponseStatusException(HttpStatus.NOT_FOUND);
            return ResponseEntity.accepted().body(result);
        }catch(RestClientException unavailable){throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE,"Return eligibility dependencies are unavailable");}
        catch(IllegalStateException conflict){throw new ResponseStatusException(HttpStatus.CONFLICT,conflict.getMessage());}
        catch(IllegalArgumentException invalid){throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,"Invalid return lines");}
    }
    @GetMapping("/{orderId}/returns/{returnId}") Map<String,Object> returnStatus(@PathVariable UUID orderId,@PathVariable UUID returnId,@AuthenticationPrincipal Jwt jwt){var result=repository.returnStatus(orderId,returnId,jwt.getSubject());if(result==null)throw new ResponseStatusException(HttpStatus.NOT_FOUND);return result;}
    @GetMapping("/{orderId}") Map<String,Object> order(@PathVariable UUID orderId,@AuthenticationPrincipal Jwt jwt){var result=repository.order(orderId,jwt.getSubject());if(result==null)throw new ResponseStatusException(HttpStatus.NOT_FOUND);return result;}
    record CancellationRequest(String reasonCode){}
    record ReturnRequest(List<ReturnRequestRules.LineInput> lines){}
    private java.time.Instant deliveredAt(Map<String,Object> shipment){
        if(shipment==null||!(shipment.get("transitions") instanceof List<?> transitions))return null;
        for(int i=transitions.size()-1;i>=0;i--){Object value=transitions.get(i);if(value instanceof Map<?,?> row&&"DELIVERED".equals(row.get("state"))&&row.get("createdAt")!=null)return java.time.Instant.parse(row.get("createdAt").toString());}
        return null;
    }
}
