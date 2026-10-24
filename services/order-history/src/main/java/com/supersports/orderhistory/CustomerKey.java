package com.supersports.orderhistory;
import java.nio.charset.StandardCharsets;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
@Component class CustomerKey {
 private final byte[] key;
 CustomerKey(@Value("${order-history.owner-key}") String key){if(key.length()<32)throw new IllegalArgumentException("Customer ownership key must contain at least 32 characters");this.key=key.getBytes(StandardCharsets.UTF_8);}
 String forSubject(String subject){try{Mac mac=Mac.getInstance("HmacSHA256");mac.init(new SecretKeySpec(key,"HmacSHA256"));return java.util.HexFormat.of().formatHex(mac.doFinal(subject.getBytes(StandardCharsets.UTF_8)));}catch(java.security.GeneralSecurityException e){throw new IllegalStateException(e);}}
}
