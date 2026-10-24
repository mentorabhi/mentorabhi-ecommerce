package com.supersports.orders;

import java.nio.charset.StandardCharsets;
import java.util.UUID;

final class PostPurchaseCancellationRules {
    private PostPurchaseCancellationRules() {}
    static boolean eligible(String orderState,String shipmentState){return "FULFILLMENT_SCHEDULED".equals(orderState)&&"SCHEDULED".equals(shipmentState);}
    static void requireCustomerReason(String reasonCode){if(!"CUSTOMER_REQUEST".equals(reasonCode))throw new IllegalArgumentException("Unsupported cancellation reason");}
    static UUID operationId(UUID operation,String purpose){if(operation==null||purpose==null||purpose.isBlank())throw new IllegalArgumentException("Invalid operation identity");return UUID.nameUUIDFromBytes((operation+":"+purpose).getBytes(StandardCharsets.UTF_8));}
    static String reasonHash(String reason){try{return java.util.HexFormat.of().formatHex(java.security.MessageDigest.getInstance("SHA-256").digest(reason.getBytes(StandardCharsets.UTF_8)));}catch(java.security.NoSuchAlgorithmException impossible){throw new IllegalStateException("SHA-256 is unavailable",impossible);}}
}
