package com.supersports.pricing;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;
@RestController @RequestMapping("/api/v1/pricing") class PricingController {
 private final PricingRepository repo;PricingController(PricingRepository repo){this.repo=repo;}
 @GetMapping("/currency") Map<String,Object> currency(){return repo.currency();}
 @GetMapping("/public/skus") List<Map<String,Object>> publicSkuPrices(@RequestParam List<UUID> skuIds){
  if(skuIds==null||skuIds.isEmpty()||skuIds.size()>100)throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,"Snapshot batch requires 1 to 100 SKU IDs");
  try{return skuIds.stream().map(repo::publicSkuPrice).toList();}catch(org.springframework.dao.EmptyResultDataAccessException e){throw new ResponseStatusException(HttpStatus.NOT_FOUND,"Price unavailable");}
 }
 @GetMapping("/public/skus/{skuId}") Map<String,Object> publicSkuPrice(@PathVariable UUID skuId){try{return repo.publicSkuPrice(skuId);}catch(org.springframework.dao.EmptyResultDataAccessException e){throw new ResponseStatusException(HttpStatus.NOT_FOUND,"Price unavailable");}}
 @GetMapping("/prices") List<Map<String,Object>> prices(){return repo.prices();}
 @PutMapping("/prices/{skuId}/{currency}") Map<String,Object> price(@PathVariable UUID skuId,@PathVariable String currency,@RequestBody PriceInput input,@AuthenticationPrincipal Jwt jwt){try{int revision=repo.setPrice(skuId,currency.toUpperCase(),input.amountMinor(),input.expectedRevision(),jwt.getSubject());return Map.of("skuId",skuId,"currency",currency.toUpperCase(),"amountMinor",input.amountMinor(),"revision",revision);}catch(StalePriceException e){throw new ResponseStatusException(HttpStatus.CONFLICT,"Price revision is stale");}catch(IllegalArgumentException e){throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,e.getMessage());}}
 @PutMapping("/currency") Map<String,Object> switchCurrency(@RequestBody CurrencyInput input){try{return repo.activateCurrency(input.currency().toUpperCase(),input.expectedRevision());}catch(StalePriceException e){throw new ResponseStatusException(HttpStatus.CONFLICT,"Currency revision is stale");}catch(IllegalArgumentException e){throw new ResponseStatusException(HttpStatus.CONFLICT,e.getMessage());}}
 @PostMapping("/completeness") Map<String,Object> completeness(@RequestBody SkuSetInput input){boolean complete=repo.complete(input.skuIds());return Map.of("complete",complete);}
 @GetMapping("/coupons") List<Map<String,Object>> coupons(){return repo.coupons();}
 @PostMapping("/coupons") Map<String,Object> coupon(@RequestBody PricingRepository.CouponInput input){try{validate(input);return Map.of("id",repo.createCoupon(input));}catch(IllegalArgumentException e){throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,e.getMessage());}}
 static void validate(PricingRepository.CouponInput c){if(c.code()==null||!c.code().matches("[A-Za-z0-9_-]{3,40}"))throw new IllegalArgumentException("Coupon code must contain 3-40 letters, digits, _ or -");Instant start=Instant.parse(c.startsAt()),end=Instant.parse(c.endsAt());if(!end.isAfter(start))throw new IllegalArgumentException("Coupon end must follow its start");if(!List.of("INR","USD").contains(c.currency().toUpperCase()))throw new IllegalArgumentException("Unsupported currency");if(!List.of("FIXED","PERCENT").contains(c.kind().toUpperCase())||c.value()<=0||(c.kind().equalsIgnoreCase("PERCENT")&&c.value()>10000))throw new IllegalArgumentException("Invalid coupon discount");if(c.minimumSubtotalMinor()<0||(c.maximumDiscountMinor()!=null&&c.maximumDiscountMinor()<=0)||(c.globalLimit()!=null&&c.globalLimit()<=0)||(c.perCustomerLimit()!=null&&c.perCustomerLimit()<=0))throw new IllegalArgumentException("Coupon limits must be positive");}
 record PriceInput(long amountMinor,int expectedRevision){} record CurrencyInput(String currency,int expectedRevision){} record SkuSetInput(List<UUID> skuIds){}
}
