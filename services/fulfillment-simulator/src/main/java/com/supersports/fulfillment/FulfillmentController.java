package com.supersports.fulfillment;

import java.util.Map;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/v1/internal/checkout/fulfillment")
class FulfillmentController {
    private final FulfillmentRepository repo;
    FulfillmentController(FulfillmentRepository repo){this.repo=repo;}

    @PostMapping
    Map<String,Object> schedule(@RequestBody Request request){
        try{return repo.schedule(UUID.fromString(request.orderId()),request.fence(),request.operationKey());}
        catch(FulfillmentRepository.StaleFenceException error){throw new ResponseStatusException(HttpStatus.CONFLICT,"Stale checkout fence");}
        catch(IllegalArgumentException error){throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,"Invalid fulfillment schedule request");}
        catch(IllegalStateException error){throw new ResponseStatusException(HttpStatus.CONFLICT,"Operation key conflict");}
    }

    @GetMapping("/{orderId}")
    Map<String,Object> status(@PathVariable UUID orderId){return repo.status(orderId);}

    @PostMapping("/{orderId}/cancel-claim")
    Map<String,Object> claimCancellation(@PathVariable UUID orderId,@RequestBody CancellationClaim request){
        try{return repo.claimCancellation(orderId,request.expectedRevision(),request.operationId());}
        catch(FulfillmentRepository.ShipmentNotFoundException error){throw new ResponseStatusException(HttpStatus.NOT_FOUND,"Shipment not found");}
        catch(FulfillmentRepository.StaleRevisionException error){throw new ResponseStatusException(HttpStatus.CONFLICT,"Shipment changed or handoff already won");}
        catch(FulfillmentRepository.InvalidTransitionException error){throw new ResponseStatusException(HttpStatus.CONFLICT,"Shipment cannot be cancelled");}
    }

    @PostMapping("/{orderId}/cancel-finalize")
    Map<String,Object> finalizeCancellation(@PathVariable UUID orderId,@RequestBody CancellationFinalize request){
        try{return repo.finalizeCancellation(orderId,request.claimOperationId(),request.operationId());}
        catch(FulfillmentRepository.ShipmentNotFoundException error){throw new ResponseStatusException(HttpStatus.NOT_FOUND,"Shipment not found");}
        catch(FulfillmentRepository.InvalidTransitionException error){throw new ResponseStatusException(HttpStatus.CONFLICT,"Cancellation claim is no longer valid");}
    }

    record Request(String orderId,long fence,String operationKey){}
    record CancellationClaim(long expectedRevision,UUID operationId){}
    record CancellationFinalize(UUID claimOperationId,UUID operationId){}
}
