package com.supersports.pricing;

import java.math.BigDecimal;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

@Repository
class PricingCheckoutRepository {
    private final JdbcTemplate jdbc;
    @Transactional void acceptCheckoutFence(UUID orderId,long fence){if(fence<1)throw new IllegalArgumentException("Checkout fence must be positive");jdbc.update("INSERT INTO checkout_order_fence(order_id,fence) VALUES (?,?) ON CONFLICT(order_id) DO UPDATE SET fence=EXCLUDED.fence,updated_at=now() WHERE checkout_order_fence.fence<=EXCLUDED.fence",orderId,fence);Long current=jdbc.queryForObject("SELECT fence FROM checkout_order_fence WHERE order_id=? FOR UPDATE",Long.class,orderId);if(current==null||current!=fence)throw new StaleCheckoutFenceException();}
    static final class StaleCheckoutFenceException extends RuntimeException{}
    PricingCheckoutRepository(JdbcTemplate jdbc){this.jdbc=jdbc;}

    @Transactional
    Map<String,Object> quote(QuoteRequest request){
        validate(request);
        String requestLock="checkout-quote:"+request.requestId();
        jdbc.query("SELECT pg_advisory_xact_lock(hashtextextended(?,0))",ps->ps.setString(1,requestLock),rs->{rs.next();return null;});
        Map<UUID,Integer> quantities=new java.util.TreeMap<>();request.lines().forEach(l->quantities.put(UUID.fromString(l.skuId()),l.quantity()));
        String requestHash=quoteHash(request,quantities);
        var prior=jdbc.queryForList("SELECT id,customer_subject,payload_hash,snapshot::text AS snapshot,expires_at FROM checkout_quote WHERE request_id=?",request.requestId());
        if(!prior.isEmpty()){
            var row=prior.getFirst();if(!request.customerSubject().equals(row.get("customer_subject"))||!requestHash.equals(row.get("payload_hash")))return Map.of("conflict",true);
            if(((Timestamp)row.get("expires_at")).toInstant().isBefore(Instant.now()))return Map.of("conflict",true,"expired",true);
            return Map.of("quoteId",row.get("id"),"replayed",true,"snapshot",Json.readMap((String)row.get("snapshot")));
        }
        var ids=new ArrayList<>(quantities.keySet());String marks=String.join(",",java.util.Collections.nCopies(ids.size(),"?"));
        var args=new ArrayList<Object>(ids);
        List<Map<String,Object>> priceRows=jdbc.queryForList("SELECT p.sku_id,p.currency,p.amount_minor,p.revision AS price_revision,c.code AS active_currency,c.revision AS currency_revision FROM store_currency c JOIN sku_price p ON p.currency=c.code WHERE c.id=1 AND p.sku_id IN ("+marks+") ORDER BY p.sku_id",args.toArray());
        if(priceRows.size()!=ids.size())throw new QuoteRejectedException("PRICE_UNAVAILABLE");
        String currency=priceRows.getFirst().get("active_currency").toString().trim();int currencyRevision=((Number)priceRows.getFirst().get("currency_revision")).intValue();
        var prices=new HashMap<UUID,Long>();var priceRevisions=new HashMap<UUID,Integer>();
        for(var row:priceRows){if(!currency.equals(row.get("currency").toString().trim()))throw new QuoteRejectedException("MIXED_CURRENCY");prices.put((UUID)row.get("sku_id"),((Number)row.get("amount_minor")).longValue());priceRevisions.put((UUID)row.get("sku_id"),((Number)row.get("price_revision")).intValue());}
        long subtotal=0;var eligibleSubtotals=new java.util.TreeMap<UUID,Long>();var lineFacts=new HashMap<UUID,QuoteLine>();
        for(var line:request.lines()){
            UUID sku=UUID.fromString(line.skuId());long amount=Math.multiplyExact(prices.get(sku),line.quantity());subtotal=Math.addExact(subtotal,amount);
            lineFacts.put(sku,line);eligibleSubtotals.put(sku,0L);
        }
        CouponData coupon=null;
        if(request.couponCode()!=null&&!request.couponCode().isBlank()){
            var coupons=jdbc.queryForList("SELECT id,code,currency,kind,value,minimum_subtotal_minor,maximum_discount_minor,rules::text AS rules,revision FROM coupon WHERE code=? AND active AND starts_at<=now() AND ends_at>now()",request.couponCode().trim().toUpperCase(java.util.Locale.ROOT));
            if(coupons.isEmpty())throw new QuoteRejectedException("COUPON_INVALID");var row=coupons.getFirst();
            if(!currency.equals(row.get("currency").toString().trim()))throw new QuoteRejectedException("COUPON_CURRENCY_MISMATCH");
            Map<String,Object> rules=Json.readMap((String)row.get("rules"));long eligibleSubtotal=0;
            for(var entry:lineFacts.entrySet())if(CouponEligibilityRules.eligible(entry.getValue().categorySlug(),rules)){
                long value=Math.multiplyExact(prices.get(entry.getKey()),entry.getValue().quantity());eligibleSubtotals.put(entry.getKey(),value);eligibleSubtotal=Math.addExact(eligibleSubtotal,value);
            }
            if(eligibleSubtotal<((Number)row.get("minimum_subtotal_minor")).longValue())throw new QuoteRejectedException("COUPON_MINIMUM_NOT_MET");
            Long maximum=row.get("maximum_discount_minor")==null?null:((Number)row.get("maximum_discount_minor")).longValue();
            long discount=CouponMath.discount(row.get("kind").toString().trim(),((Number)row.get("value")).longValue(),eligibleSubtotal,maximum);
            var allocations=CouponMath.allocate(discount,eligibleSubtotals);coupon=new CouponData((UUID)row.get("id"),((Number)row.get("revision")).intValue(),discount,allocations);
        }
        var quoteLines=new ArrayList<Map<String,Object>>();
        long allocatedDiscount=0;for(UUID sku:ids){QuoteLine fact=lineFacts.get(sku);long unit=prices.get(sku),lineSubtotal=Math.multiplyExact(unit,fact.quantity());long discount=coupon==null?0:coupon.allocations().getOrDefault(sku,0L);allocatedDiscount=Math.addExact(allocatedDiscount,discount);var lineQuote=new LinkedHashMap<String,Object>();lineQuote.put("skuId",sku);lineQuote.put("productId",fact.productId());lineQuote.put("productTitle",fact.productTitle());lineQuote.put("categoryId",fact.categoryId());lineQuote.put("categorySlug",fact.categorySlug());lineQuote.put("quantity",fact.quantity());lineQuote.put("unitPriceMinor",unit);lineQuote.put("subtotalMinor",lineSubtotal);lineQuote.put("discountMinor",discount);lineQuote.put("lineTotalMinor",Math.subtractExact(lineSubtotal,discount));lineQuote.put("currency",currency);lineQuote.put("priceRevision",priceRevisions.get(sku));lineQuote.put("catalogRevisions",Map.of("sku",fact.skuRevision(),"product",fact.productRevision(),"category",fact.categoryRevision()));quoteLines.add(lineQuote);}
        UUID quoteId=UUID.randomUUID();Instant expiry=Instant.now().plusSeconds(300);var snapshot=new LinkedHashMap<String,Object>();snapshot.put("quoteId",quoteId);snapshot.put("currency",currency);snapshot.put("currencyRevision",currencyRevision);snapshot.put("subtotalMinor",subtotal);snapshot.put("discountMinor",allocatedDiscount);snapshot.put("merchandiseTotalMinor",Math.subtractExact(subtotal,allocatedDiscount));snapshot.put("couponCode",coupon==null?null:request.couponCode().trim().toUpperCase(java.util.Locale.ROOT));snapshot.put("couponRevision",coupon==null?null:coupon.revision());snapshot.put("lines",quoteLines);snapshot.put("expiresAt",expiry.toString());
        jdbc.update("INSERT INTO checkout_quote(id,request_id,customer_subject,payload_hash,currency,currency_revision,subtotal_minor,discount_minor,coupon_id,coupon_revision,snapshot,expires_at) VALUES (?,?,?,?,?,?,?,?,?,?,?::jsonb,?)",quoteId,request.requestId(),request.customerSubject(),requestHash,currency,currencyRevision,subtotal,allocatedDiscount,coupon==null?null:coupon.id(),coupon==null?null:coupon.revision(),Json.write(snapshot),Timestamp.from(expiry));
        return Map.of("quoteId",quoteId,"replayed",false,"snapshot",snapshot);
    }

    @Transactional
    Map<String,Object> hold(HoldRequest request){
        if(request==null||request.orderId()==null||request.quoteId()==null||request.customerSubject()==null||request.expiresAt()==null)throw new IllegalArgumentException("Invalid coupon hold");
        Instant now=Instant.now(),expiry=Instant.parse(request.expiresAt());if(!expiry.isAfter(now)||expiry.isAfter(now.plusSeconds(1800)))throw new IllegalArgumentException("Coupon hold expiry must be within 30 minutes");
        var quoteRows=jdbc.queryForList("SELECT id,customer_subject,coupon_id,discount_minor,currency,currency_revision,coupon_revision,snapshot::text AS snapshot,expires_at FROM checkout_quote WHERE id=? FOR UPDATE",UUID.fromString(request.quoteId()));if(quoteRows.isEmpty())throw new QuoteRejectedException("QUOTE_NOT_FOUND");var quote=quoteRows.getFirst();
        UUID order=UUID.fromString(request.orderId());var prior=jdbc.queryForList("SELECT id,quote_id,customer_subject,state FROM coupon_checkout_hold WHERE order_id=? FOR UPDATE",order);
        if(!prior.isEmpty()){var old=prior.getFirst();if(!old.get("quote_id").equals(quote.get("id"))||!old.get("customer_subject").equals(request.customerSubject()))return Map.of("conflict",true);return Map.of("holdId",old.get("id"),"state",old.get("state"),"replayed",true);}
        if(!request.customerSubject().equals(quote.get("customer_subject"))||((Timestamp)quote.get("expires_at")).toInstant().isBefore(now))throw new QuoteRejectedException("QUOTE_EXPIRED_OR_OWNER_MISMATCH");
        var activeCurrency=jdbc.queryForMap("SELECT code,revision FROM store_currency WHERE id=1");if(!quote.get("currency").toString().trim().equals(activeCurrency.get("code").toString().trim())||((Number)quote.get("currency_revision")).intValue()!=((Number)activeCurrency.get("revision")).intValue())throw new QuoteRejectedException("QUOTE_REVISIONS_CHANGED");
        Map<String,Object> quoteSnapshot=Json.readMap((String)quote.get("snapshot"));for(Object raw:(List<?>)quoteSnapshot.get("lines")){Map<String,Object> line=(Map<String,Object>)raw;var current=jdbc.queryForList("SELECT revision FROM sku_price WHERE sku_id=? AND currency=?",UUID.fromString(line.get("skuId").toString()),quote.get("currency"));if(current.isEmpty()||((Number)current.getFirst().get("revision")).intValue()!=((Number)line.get("priceRevision")).intValue())throw new QuoteRejectedException("QUOTE_REVISIONS_CHANGED");}
        if(quote.get("coupon_id")==null)return Map.of("couponRequired",false,"replayed",false);
        UUID couponId=(UUID)quote.get("coupon_id");var coupons=jdbc.queryForList("SELECT id,active,starts_at,ends_at,global_limit,per_customer_limit,revision FROM coupon WHERE id=? FOR UPDATE",couponId);if(coupons.isEmpty())throw new QuoteRejectedException("COUPON_INVALID");var coupon=coupons.getFirst();
        if(!Boolean.TRUE.equals(coupon.get("active"))||((Timestamp)coupon.get("starts_at")).toInstant().isAfter(now)||!((Timestamp)coupon.get("ends_at")).toInstant().isAfter(now)||((Number)coupon.get("revision")).intValue()!=((Number)quote.get("coupon_revision")).intValue())throw new QuoteRejectedException("COUPON_CHANGED");
        long global=((Number)jdbc.queryForObject("SELECT count(*) FROM coupon_checkout_hold WHERE coupon_id=? AND (state='COMMITTED' OR state='PROTECTED' OR (state='HELD' AND expires_at>now()))",Long.class,couponId)).longValue();long globalLimit=coupon.get("global_limit")==null?Long.MAX_VALUE:((Number)coupon.get("global_limit")).longValue();if(global>=globalLimit)throw new QuoteRejectedException("COUPON_LIMIT_REACHED");
        if(coupon.get("per_customer_limit")!=null){long owned=jdbc.queryForObject("SELECT count(*) FROM coupon_checkout_hold WHERE coupon_id=? AND customer_subject=? AND (state='COMMITTED' OR state='PROTECTED' OR (state='HELD' AND expires_at>now()))",Long.class,couponId,request.customerSubject());if(owned>=((Number)coupon.get("per_customer_limit")).intValue())throw new QuoteRejectedException("CUSTOMER_COUPON_LIMIT_REACHED");}
        UUID holdId=UUID.randomUUID();long discount=((Number)quote.get("discount_minor")).longValue();jdbc.update("INSERT INTO coupon_checkout_hold(id,order_id,quote_id,coupon_id,customer_subject,discount_minor,state,expires_at) VALUES (?,?,?,?,?,?,'HELD',?)",holdId,order,quote.get("id"),couponId,request.customerSubject(),discount,Timestamp.from(expiry));return Map.of("holdId",holdId,"state","HELD","replayed",false);
    }

    @Transactional Map<String,Object> transition(UUID orderId,String target){
        var rows=jdbc.queryForList("SELECT id,state,expires_at FROM coupon_checkout_hold WHERE order_id=? FOR UPDATE",orderId);if(rows.isEmpty())throw new QuoteRejectedException("HOLD_NOT_FOUND");var row=rows.getFirst();String state=row.get("state").toString();
        if(state.equals(target))return Map.of("orderId",orderId,"state",state,"replayed",true);
        if(target.equals("PROTECTED")&&!state.equals("HELD"))throw new QuoteRejectedException("INVALID_HOLD_TRANSITION");
        if((target.equals("COMMITTED")||target.equals("RELEASED"))&&!List.of("HELD","PROTECTED").contains(state))throw new QuoteRejectedException("INVALID_HOLD_TRANSITION");
        if(state.equals("HELD")&&((Timestamp)row.get("expires_at")).toInstant().isBefore(Instant.now()))throw new QuoteRejectedException("HOLD_EXPIRED");
        jdbc.update("UPDATE coupon_checkout_hold SET state=?,updated_at=now() WHERE id=?",target,row.get("id"));return Map.of("orderId",orderId,"state",target,"replayed",false);
    }

    private static void validate(QuoteRequest r){if(r==null||r.requestId()==null||r.customerSubject()==null||r.customerSubject().isBlank()||r.lines()==null||r.lines().isEmpty()||r.lines().size()>50)throw new IllegalArgumentException("Invalid quote request");var ids=new java.util.HashSet<String>();for(var l:r.lines())if(l==null||l.skuId()==null||l.quantity()<=0||l.quantity()>100||l.productId()==null||l.productTitle()==null||l.categoryId()==null||l.categorySlug()==null||!ids.add(l.skuId()))throw new IllegalArgumentException("Invalid quote line");}
    private static String quoteHash(QuoteRequest r,Map<UUID,Integer> quantities){String payload=r.customerSubject()+"|"+r.couponCode()+"|"+quantities+"|"+r.lines().stream().sorted(java.util.Comparator.comparing(QuoteLine::skuId)).map(l->l.skuId()+":"+l.productId()+":"+l.productTitle()+":"+l.categoryId()+":"+l.categorySlug()+":"+l.skuRevision()+":"+l.productRevision()+":"+l.categoryRevision()).toList();try{return java.util.HexFormat.of().formatHex(java.security.MessageDigest.getInstance("SHA-256").digest(payload.getBytes(java.nio.charset.StandardCharsets.UTF_8)));}catch(java.security.NoSuchAlgorithmException e){throw new IllegalStateException(e);}}
    record QuoteLine(String skuId,int quantity,String productId,String productTitle,String categoryId,String categorySlug,int skuRevision,int productRevision,int categoryRevision){}
    record QuoteRequest(UUID requestId,String customerSubject,String couponCode,List<QuoteLine> lines){}
    record HoldRequest(String orderId,String quoteId,String customerSubject,String expiresAt,long fence){}
    private record CouponData(UUID id,int revision,long discount,Map<UUID,Long> allocations){}
    static final class QuoteRejectedException extends RuntimeException{QuoteRejectedException(String code){super(code);}}
}
