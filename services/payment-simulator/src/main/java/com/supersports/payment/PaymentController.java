package com.supersports.payment;
import java.util.Map;import java.util.UUID;import org.springframework.http.HttpStatus;import org.springframework.web.bind.annotation.*;import org.springframework.web.server.ResponseStatusException;
@RestController @RequestMapping("/api/v1/internal/checkout/payments")
class PaymentController {
 private final PaymentSimulator simulator; PaymentController(PaymentSimulator simulator){this.simulator=simulator;}
 @PostMapping("/{operation}") Map<String,Object> execute(@PathVariable String operation,@RequestBody Request r){try{return simulator.execute(UUID.fromString(r.orderId()),operation.toUpperCase(),r.operationKey(),r.fence(),r.amountMinor(),r.currency(),r.authorizationMode()==null?"APPROVE":r.authorizationMode());}catch(PaymentSimulator.StaleFenceException e){throw new ResponseStatusException(HttpStatus.CONFLICT,"Stale checkout fence");}catch(PaymentSimulator.OperationConflictException e){throw new ResponseStatusException(HttpStatus.CONFLICT,"Operation key payload conflict");}catch(IllegalArgumentException e){throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,e.getMessage());}catch(IllegalStateException e){throw new ResponseStatusException(HttpStatus.CONFLICT,"Payment operation is not valid in the current state");}}
 @GetMapping("/{orderId}/status") Map<String,Object> status(@PathVariable UUID orderId){return simulator.status(orderId);}
 record Request(String orderId,String operationKey,long fence,long amountMinor,String currency,String authorizationMode){}
}
