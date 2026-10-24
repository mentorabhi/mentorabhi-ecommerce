package com.supersports.fulfillment;

import java.util.Map;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/v1/operator/shipments")
class ShipmentOperatorController {
    private final FulfillmentRepository repository;
    ShipmentOperatorController(FulfillmentRepository repository){this.repository=repository;}

    @org.springframework.web.bind.annotation.GetMapping("/{orderId}")
    Map<String,Object> shipment(@PathVariable UUID orderId){var result=repository.status(orderId);if(result==null)throw new ResponseStatusException(HttpStatus.NOT_FOUND,"Shipment not found");return result;}

    @PostMapping("/{orderId}/transitions")
    Map<String,Object> advance(@PathVariable UUID orderId,@RequestBody Request request,@AuthenticationPrincipal Jwt operator){
        if(request==null||request.operationId()==null||request.targetState()==null||request.reason()==null)
            throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,"Invalid shipment transition request");
        try{return repository.advance(orderId,request.expectedRevision(),UUID.fromString(request.operationId()),request.targetState(),request.reason(),operator.getSubject());}
        catch(FulfillmentRepository.ShipmentNotFoundException error){throw new ResponseStatusException(HttpStatus.NOT_FOUND,"Shipment not found");}
        catch(FulfillmentRepository.StaleRevisionException error){throw new ResponseStatusException(HttpStatus.CONFLICT,"Shipment revision changed");}
        catch(FulfillmentRepository.OperationConflictException error){throw new ResponseStatusException(HttpStatus.CONFLICT,"Operation ID conflicts with an earlier request");}
        catch(FulfillmentRepository.InvalidTransitionException error){throw new ResponseStatusException(HttpStatus.CONFLICT,"Shipment state transition is not allowed");}
        catch(IllegalArgumentException error){throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,"Invalid shipment transition request");}
    }

    record Request(long expectedRevision,String operationId,String targetState,String reason){}
}
