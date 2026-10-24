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

    record Request(String orderId,long fence,String operationKey){}
}
