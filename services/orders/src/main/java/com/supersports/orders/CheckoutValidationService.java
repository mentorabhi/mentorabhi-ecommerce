package com.supersports.orders;

import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.web.client.RestClient;

@Service
class CheckoutValidationService {
    private final OrdersRepository repository;
    private final RestClient customer, catalog, pricing, configuration, identity;
    private final String clientId, clientSecret;
    private volatile String cachedToken;
    private volatile Instant tokenExpiry=Instant.EPOCH;

    CheckoutValidationService(OrdersRepository repository,
            @Value("${customer.base-url}") String customerUrl,
            @Value("${catalog.base-url}") String catalogUrl,
            @Value("${pricing.base-url}") String pricingUrl,
            @Value("${configuration.base-url}") String configurationUrl,
            @Value("${identity.token-url}") String tokenUrl,
            @Value("${checkout.worker-client-id}") String clientId,
            @Value("${checkout.worker-client-secret}") String clientSecret) {
        this.repository=repository;customer=RestClient.builder().baseUrl(customerUrl).build();catalog=RestClient.builder().baseUrl(catalogUrl).build();pricing=RestClient.builder().baseUrl(pricingUrl).build();configuration=RestClient.builder().baseUrl(configurationUrl).build();identity=RestClient.builder().baseUrl(tokenUrl.substring(0,tokenUrl.indexOf("/realms/"))).build();this.clientId=clientId;this.clientSecret=clientSecret;
    }

    Map<String,Object> validate(UUID requestId,String subject,String customerToken,Map<UUID,Integer> lines,String coupon) {
        var address=customer.get().uri("/api/v1/customer/profile").header("Authorization","Bearer "+customerToken).retrieve().body(Map.class);
        if(address==null||!present(address,"fullName","line1","city","state","postalCode")||!"IN".equals(address.get("country")))throw new CheckoutRejectedException("CUSTOMER_ADDRESS_REQUIRED");
        String worker=workerToken();var quoteLines=new ArrayList<Map<String,Object>>();
        for(var entry:lines.entrySet()){
            Map<String,Object> fact=catalog.get().uri("/api/v1/internal/checkout/catalog/skus/{sku}",entry.getKey()).header("Authorization","Bearer "+worker).retrieve().body(Map.class);
            if(fact==null||!Boolean.TRUE.equals(fact.get("active")))throw new CheckoutRejectedException("SKU_UNAVAILABLE");
            var line=new LinkedHashMap<String,Object>();line.put("skuId",entry.getKey().toString());line.put("quantity",entry.getValue());line.put("productId",fact.get("productId").toString());line.put("productTitle",fact.get("title"));line.put("categoryId",fact.get("categoryId").toString());line.put("categorySlug",fact.get("categorySlug"));line.put("skuRevision",fact.get("skuRevision"));line.put("productRevision",fact.get("productRevision"));line.put("categoryRevision",fact.get("categoryRevision"));quoteLines.add(line);
        }
        var quoteRequest=new LinkedHashMap<String,Object>();quoteRequest.put("requestId",requestId);quoteRequest.put("customerSubject",subject);quoteRequest.put("couponCode",coupon);quoteRequest.put("lines",quoteLines);
        Map<String,Object> quote=pricing.post().uri("/api/v1/internal/checkout/pricing/quotes").contentType(MediaType.APPLICATION_JSON).header("Authorization","Bearer "+worker).body(quoteRequest).retrieve().body(Map.class);
        Map<String,Object> settings=configuration.get().uri("/api/v1/internal/checkout/configuration").header("Authorization","Bearer "+worker).retrieve().body(Map.class);
        if(quote==null||settings==null)throw new IllegalStateException("Checkout validation service returned an empty response");
        Map<String,Object> snapshot=(Map<String,Object>)quote.get("snapshot");String currency=snapshot.get("currency").toString();long taxable=((Number)snapshot.get("merchandiseTotalMinor")).longValue();int bps=((Number)settings.get("taxRateBps")).intValue();long tax=CheckoutMoney.tax(taxable,bps);long shipping=((Number)settings.get(currency.equals("INR")?"shippingInrMinor":"shippingUsdMinor")).longValue();long total=CheckoutMoney.total(taxable,tax,shipping);
        UUID orderId=UUID.randomUUID();return repository.accept(requestId,subject,orderId,address,quote,settings,((Number)settings.get("revision")).longValue(),tax,shipping,total);
    }

    private synchronized String workerToken(){if(cachedToken!=null&&tokenExpiry.isAfter(Instant.now().plusSeconds(30)))return cachedToken;
        var form=new LinkedMultiValueMap<String,String>();form.add("grant_type","client_credentials");form.add("client_id",clientId);form.add("client_secret",clientSecret);
        Map body=identity.post().uri("/realms/supersports/protocol/openid-connect/token").contentType(MediaType.APPLICATION_FORM_URLENCODED).body(form).retrieve().body(Map.class);
        if(body==null||body.get("access_token")==null)throw new IllegalStateException("Checkout service identity token unavailable");cachedToken=body.get("access_token").toString();tokenExpiry=Instant.now().plusSeconds(((Number)body.getOrDefault("expires_in",60)).longValue());return cachedToken;
    }
    private static boolean present(Map<String,Object> m,String...keys){for(String k:keys)if(m.get(k)==null||m.get(k).toString().isBlank())return false;return true;}
    static final class CheckoutRejectedException extends RuntimeException{CheckoutRejectedException(String code){super(code);}}
}
