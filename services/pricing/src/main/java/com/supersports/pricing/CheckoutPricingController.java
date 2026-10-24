package com.supersports.pricing;
import java.util.Map;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController @RequestMapping("/api/v1/internal/checkout/pricing")
class CheckoutPricingController {
    private final PricingCheckoutRepository repository;
    CheckoutPricingController(PricingCheckoutRepository repository){this.repository=repository;}
    @PostMapping("/quotes") Map<String,Object> quote(@RequestBody PricingCheckoutRepository.QuoteRequest request){
        try{Map<String,Object> result=repository.quote(request);if(Boolean.TRUE.equals(result.get("conflict")))throw new ResponseStatusException(HttpStatus.CONFLICT,"Quote request conflicts with an earlier request or revisions");return result;}
        catch(PricingCheckoutRepository.QuoteRejectedException e){throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,e.getMessage());}
        catch(ArithmeticException|IllegalArgumentException e){throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,"Invalid quote request");}
    }
    @PostMapping("/coupon-holds") @org.springframework.transaction.annotation.Transactional Map<String,Object> hold(@RequestBody PricingCheckoutRepository.HoldRequest request){
        try{repository.acceptCheckoutFence(UUID.fromString(request.orderId()),request.fence());Map<String,Object> result=repository.hold(request);if(Boolean.TRUE.equals(result.get("conflict")))throw new ResponseStatusException(HttpStatus.CONFLICT,"Coupon hold conflicts with a prior order operation");return result;}
        catch(PricingCheckoutRepository.StaleCheckoutFenceException e){throw new ResponseStatusException(HttpStatus.CONFLICT,"Stale checkout fence");}
        catch(PricingCheckoutRepository.QuoteRejectedException e){throw new ResponseStatusException(HttpStatus.CONFLICT,e.getMessage());}
        catch(IllegalArgumentException e){throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,"Invalid coupon hold");}
    }
    @PostMapping("/coupon-holds/{orderId}/protect") @org.springframework.transaction.annotation.Transactional Map<String,Object> protect(@PathVariable UUID orderId,@RequestHeader("X-Checkout-Fence")long fence){return transition(orderId,fence,"PROTECTED");}
    @PostMapping("/coupon-holds/{orderId}/commit") @org.springframework.transaction.annotation.Transactional Map<String,Object> commit(@PathVariable UUID orderId,@RequestHeader("X-Checkout-Fence")long fence){return transition(orderId,fence,"COMMITTED");}
    @PostMapping("/coupon-holds/{orderId}/release") @org.springframework.transaction.annotation.Transactional Map<String,Object> release(@PathVariable UUID orderId,@RequestHeader("X-Checkout-Fence")long fence){return transition(orderId,fence,"RELEASED");}
    private Map<String,Object> transition(UUID orderId,long fence,String target){try{repository.acceptCheckoutFence(orderId,fence);return repository.transition(orderId,target);}catch(PricingCheckoutRepository.StaleCheckoutFenceException e){throw new ResponseStatusException(HttpStatus.CONFLICT,"Stale checkout fence");}catch(PricingCheckoutRepository.QuoteRejectedException e){throw new ResponseStatusException(HttpStatus.CONFLICT,e.getMessage());}}
}
