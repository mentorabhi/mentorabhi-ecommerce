package com.supersports.orders;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.web.client.RestClient;

@Component
class CheckoutSagaWorker {
    private final OrdersRepository orders;
    private final RestClient inventory,payment,pricing,fulfillment,configuration,identity;
    private final String clientId,clientSecret;
    private volatile String token;
    private volatile Instant expiry=Instant.EPOCH;

    CheckoutSagaWorker(OrdersRepository orders,
            @Value("${inventory.base-url}") String inventoryUrl,
            @Value("${payment.base-url}") String paymentUrl,
            @Value("${pricing.base-url}") String pricingUrl,
            @Value("${fulfillment.base-url}") String fulfillmentUrl,
            @Value("${configuration.base-url}") String configurationUrl,
            @Value("${identity.token-url}") String tokenUrl,
            @Value("${checkout.worker-client-id}") String clientId,
            @Value("${checkout.worker-client-secret}") String clientSecret) {
        this.orders=orders; inventory=RestClient.builder().baseUrl(inventoryUrl).build();
        payment=RestClient.builder().baseUrl(paymentUrl).build(); pricing=RestClient.builder().baseUrl(pricingUrl).build();
        fulfillment=RestClient.builder().baseUrl(fulfillmentUrl).build();configuration=RestClient.builder().baseUrl(configurationUrl).build();identity=RestClient.builder().baseUrl(tokenUrl.substring(0,tokenUrl.indexOf("/realms/"))).build();
        this.clientId=clientId;this.clientSecret=clientSecret;
    }

    @Scheduled(fixedDelayString="${checkout.worker-poll-ms:1000}")
    void poll(){
        Map<String,Object> claim=orders.claimSaga();if(claim==null)return;
        UUID id=(UUID)claim.get("order_id");String step=claim.get("current_step").toString();long fence=((Number)claim.get("fence")).longValue();
        try{advance(id,step,fence);}catch(PaymentDeclinedException e){compensateDeclined(id,fence);}catch(RuntimeException e){orders.sagaRetry(id,fence,"CHECKOUT_STEP_RETRY");}
    }

    @Scheduled(fixedDelayString="${checkout.worker-poll-ms:1000}")
    void pollPostPurchase(){
        Map<String,Object> claim=orders.claimPostPurchase();if(claim==null)return;
        UUID operation=(UUID)claim.get("operation_id"),order=(UUID)claim.get("order_id");
        String step=claim.get("current_step").toString();long fence=((Number)claim.get("fence")).longValue();
        try{advanceCancellation(operation,order,step,fence,claim);}
        catch(org.springframework.web.client.HttpClientErrorException.Conflict conflict){
            if("CLAIM_SHIPMENT".equals(step))orders.postPurchaseReject(operation,fence,"HANDOFF_WON");
            else orders.postPurchaseManualReview(operation,fence,"CANCELLATION_CONFLICT");
        }catch(RuntimeException failure){orders.postPurchaseRetry(operation,fence,"CANCELLATION_STEP_RETRY");}
    }

    @Scheduled(fixedDelayString="${checkout.worker-poll-ms:1000}")
    void pollReturns(){
        Map<String,Object> claim=orders.claimReturn();if(claim==null)return;
        UUID returnId=(UUID)claim.get("return_id");long fence=((Number)claim.get("fence")).longValue();long amount=((Number)claim.get("amount_minor")).longValue();
        try{
            if(amount>0){UUID order=(UUID)claim.get("order_id");
                Map<String,Object> receipt=payment.post().uri("/api/v1/internal/checkout/payments/refund").header("Authorization","Bearer "+workerToken()).contentType(MediaType.APPLICATION_JSON)
                    .body(Map.of("orderId",order.toString(),"operationKey","return:"+returnId+":refund","fence",fence,"amountMinor",amount,"currency",claim.get("currency").toString().trim(),"authorizationMode","APPROVE")).retrieve().body(Map.class);
                if(receipt==null||!"REFUNDED".equals(receipt.get("state"))){orders.manualReviewReturn(returnId,fence,"PAYMENT_REFUND_UNCONFIRMED");return;}
            }
            orders.completeReturn(returnId,fence);
        }catch(org.springframework.web.client.HttpClientErrorException.Conflict conflict){orders.manualReviewReturn(returnId,fence,"PAYMENT_REFUND_CONFLICT");}
        catch(RuntimeException failure){orders.retryReturn(returnId,fence,"RETURN_REFUND_RETRY");}
    }

    private void advanceCancellation(UUID operation,UUID order,String step,long fence,Map<String,Object> claim){
        String bearer="Bearer "+workerToken();UUID claimId=operationId(operation,"shipment-claim");Map<String,Object> result;String next;
        switch(step){
            case "CLAIM_SHIPMENT" -> {result=fulfillment.post().uri("/api/v1/internal/checkout/fulfillment/{id}/cancel-claim",order).header("Authorization",bearer).contentType(MediaType.APPLICATION_JSON).body(Map.of("expectedRevision",claim.get("expected_shipment_revision"),"operationId",claimId)).retrieve().body(Map.class);next="REFUND_PAYMENT";}
            case "REFUND_PAYMENT" -> {
                long amount=((Number)claim.get("total_minor")).longValue();
                if(amount==0)result=Map.of("state","SKIPPED","amountMinor",0L);
                else result=payment.post().uri("/api/v1/internal/checkout/payments/refund").header("Authorization",bearer).contentType(MediaType.APPLICATION_JSON).body(Map.of("orderId",order.toString(),"operationKey","cancel:"+operation+":refund","fence",fence,"amountMinor",amount,"currency",claim.get("currency"),"authorizationMode","APPROVE")).retrieve().body(Map.class);
                next="RESTOCK_INVENTORY";
            }
            case "RESTOCK_INVENTORY" -> {result=inventory.post().uri("/api/v1/internal/checkout/inventory/reservations/{id}/cancel",order).header("Authorization",bearer).contentType(MediaType.APPLICATION_JSON).body(Map.of("operationId",operationId(operation,"inventory-restock"),"fence",fence)).retrieve().body(Map.class);next="FINALIZE_SHIPMENT";}
            case "FINALIZE_SHIPMENT" -> {result=fulfillment.post().uri("/api/v1/internal/checkout/fulfillment/{id}/cancel-finalize",order).header("Authorization",bearer).contentType(MediaType.APPLICATION_JSON).body(Map.of("claimOperationId",claimId,"operationId",operationId(operation,"shipment-finalize"))).retrieve().body(Map.class);result=new LinkedHashMap<>(result);result.put("refundMinor",claim.get("total_minor"));result.put("currency",claim.get("currency"));next="DONE";}
            default -> {orders.postPurchaseManualReview(operation,fence,"UNKNOWN_CANCELLATION_STEP");return;}
        }
        String opKey="cancel:"+operation+":"+step.toLowerCase(java.util.Locale.ROOT);
        orders.postPurchaseStep(operation,fence,step,next,step,opKey,result==null?Map.of():result);
    }

    private UUID operationId(UUID parent,String purpose){return PostPurchaseCancellationRules.operationId(parent,purpose);}

    private void advance(UUID id,String step,long fence){
        Map<String,Object> order=orders.sagaOrder(id);if(order==null)return;
        Map<String,Object> quote=(Map<String,Object>)order.get("quoteSnapshot");String bearer="Bearer "+workerToken();Map<String,Object> settings=(Map<String,Object>)quote.get("simulationSettings");
        if("RESERVE_INVENTORY".equals(step)&&CheckoutRules.quoteExpired(quote.get("expiresAt"),Instant.now())){orders.failExpiredQuote(id,fence);return;}
        if(settings==null){settings=configuration.get().uri("/api/v1/internal/checkout/configuration").header("Authorization",bearer).retrieve().body(Map.class);if(settings==null)throw new IllegalStateException("Checkout settings are unavailable");orders.repairMissingSimulationSettings(id,fence,settings);quote.put("simulationSettings",settings);}
        Map<String,Object> result=new LinkedHashMap<>();String next;
        switch(step){
            case "RESERVE_INVENTORY" -> {
                var body=new LinkedHashMap<String,Object>();body.put("orderId",id);body.put("expiresAt",Instant.now().plusSeconds(((Number)settings.get("reservationSeconds")).longValue()).toString());body.put("lines",order.get("lines"));body.put("fence",fence);
                result=inventory.post().uri("/api/v1/internal/checkout/inventory/reservations").header("Authorization",bearer).contentType(MediaType.APPLICATION_JSON).body(body).retrieve().body(Map.class);next="HOLD_COUPON";
            }
            case "HOLD_COUPON" -> {
                var body=Map.of("orderId",id.toString(),"quoteId",quote.get("quoteId").toString(),"customerSubject",order.get("customerSubject").toString(),"expiresAt",Instant.now().plusSeconds(((Number)settings.get("reservationSeconds")).longValue()).toString(),"fence",fence);result=pricing.post().uri("/api/v1/internal/checkout/pricing/coupon-holds").header("Authorization",bearer).contentType(MediaType.APPLICATION_JSON).body(body).retrieve().body(Map.class);next="AUTHORIZE";
            }
            case "AUTHORIZE" -> {result=payment.post().uri("/api/v1/internal/checkout/payments/authorize").header("Authorization",bearer).contentType(MediaType.APPLICATION_JSON).body(paymentBody(id,step,fence,order,settings)).retrieve().body(Map.class);if("DECLINED".equals(result.get("state")))throw new PaymentDeclinedException();next="PROTECT_HOLDS";}
            case "PROTECT_HOLDS" -> {result=inventory.post().uri("/api/v1/internal/checkout/inventory/reservations/{id}/protect",id).header("Authorization",bearer).header("X-Checkout-Fence",Long.toString(fence)).retrieve().body(Map.class);if(hasCoupon(quote))pricing.post().uri("/api/v1/internal/checkout/pricing/coupon-holds/{id}/protect",id).header("Authorization",bearer).header("X-Checkout-Fence",Long.toString(fence)).retrieve().body(Map.class);next="CAPTURE";}
            case "CAPTURE" -> {result=payment.post().uri("/api/v1/internal/checkout/payments/capture").header("Authorization",bearer).contentType(MediaType.APPLICATION_JSON).body(paymentBody(id,step,fence,order,settings)).retrieve().body(Map.class);next="COMMIT_INVENTORY";}
            case "COMMIT_INVENTORY" -> {result=inventory.post().uri("/api/v1/internal/checkout/inventory/reservations/{id}/commit",id).header("Authorization",bearer).header("X-Checkout-Fence",Long.toString(fence)).retrieve().body(Map.class);next=hasCoupon(quote)?"COMMIT_COUPON":"CONFIRM";}
            case "COMMIT_COUPON" -> {result=pricing.post().uri("/api/v1/internal/checkout/pricing/coupon-holds/{id}/commit",id).header("Authorization",bearer).header("X-Checkout-Fence",Long.toString(fence)).retrieve().body(Map.class);next="CONFIRM";}
            case "CONFIRM" -> {result=Map.of("state","CONFIRMED");next="DONE";}
            case "SCHEDULE_FULFILLMENT" -> {result=fulfillment.post().uri("/api/v1/internal/checkout/fulfillment").header("Authorization",bearer).contentType(MediaType.APPLICATION_JSON).body(Map.of("orderId",id.toString(),"fence",fence,"operationKey",id+":schedule-fulfillment")).retrieve().body(Map.class);next="FULFILLMENT_DONE";}
            default -> {orders.sagaRetry(id,fence,"UNKNOWN_SAGA_STEP");return;}
        }
        orders.sagaStep(id,fence,step,next,step,result==null?Map.of():result);
    }

    private Map<String,Object> paymentBody(UUID id,String step,long fence,Map<String,Object> order,Map<String,Object> settings){
        String operation=switch(step){case "AUTHORIZE"->"authorize";case "CAPTURE"->"capture";default->step.toLowerCase(java.util.Locale.ROOT);};
        return Map.of("orderId",id.toString(),"operationKey",id+":"+operation,"fence",fence,"amountMinor",((Number)order.get("totalMinor")).longValue(),"currency",order.get("currency").toString(),"authorizationMode",settings.get("authorizationMode").toString());
    }
    Map<String,Object> fulfillmentStatus(UUID orderId){
        return fulfillment.get().uri("/api/v1/internal/checkout/fulfillment/{orderId}",orderId)
            .header("Authorization","Bearer "+workerToken()).retrieve().body(Map.class);
    }
    Map<String,Object> returnsPolicy(){
        return configuration.get().uri("/api/v1/internal/checkout/configuration/returns-policy")
            .header("Authorization","Bearer "+workerToken()).retrieve().body(Map.class);
    }
    private void compensateDeclined(UUID id,long fence){
        try{String bearer="Bearer "+workerToken();inventory.post().uri("/api/v1/internal/checkout/inventory/reservations/{id}/release",id).header("Authorization",bearer).header("X-Checkout-Fence",Long.toString(fence)).retrieve().body(Map.class);Map<String,Object> o=orders.sagaOrder(id);Map<String,Object> q=(Map<String,Object>)o.get("quoteSnapshot");if(hasCoupon(q))pricing.post().uri("/api/v1/internal/checkout/pricing/coupon-holds/{id}/release",id).header("Authorization",bearer).header("X-Checkout-Fence",Long.toString(fence)).retrieve().body(Map.class);orders.failDeclined(id,fence);}catch(RuntimeException e){orders.sagaRetry(id,fence,"PAYMENT_DECLINE_COMPENSATION_RETRY");}
    }
    private boolean hasCoupon(Map<String,Object> q){return q.get("couponCode")!=null&&!q.get("couponCode").toString().isBlank();}
    private synchronized String workerToken(){if(token!=null&&expiry.isAfter(Instant.now().plusSeconds(30)))return token;var form=new LinkedMultiValueMap<String,String>();form.add("grant_type","client_credentials");form.add("client_id",clientId);form.add("client_secret",clientSecret);Map body=identity.post().uri("/realms/supersports/protocol/openid-connect/token").contentType(MediaType.APPLICATION_FORM_URLENCODED).body(form).retrieve().body(Map.class);if(body==null||body.get("access_token")==null)throw new IllegalStateException("Checkout service identity token unavailable");token=body.get("access_token").toString();expiry=Instant.now().plusSeconds(((Number)body.getOrDefault("expires_in",60)).longValue());return token;}
    private static final class PaymentDeclinedException extends RuntimeException{}
}
