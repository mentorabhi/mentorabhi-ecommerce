package com.supersports.customer;

import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.security.oauth2.jwt.Jwt;
import static org.assertj.core.api.Assertions.*;

class CustomerSecurityTest {
    private final CustomerSecurity security = new CustomerSecurity();

    @Test void customerAudienceIsRequired() {
        var validator = security.customerAudience();
        assertThat(validator.validate(token(List.of("supersports-customer-api"))).hasErrors()).isFalse();
        assertThat(validator.validate(token(List.of("supersports-api"))).hasErrors()).isTrue();
        assertThat(validator.validate(token(List.of())).hasErrors()).isTrue();
    }

    private static Jwt token(List<String> audience) {
        return Jwt.withTokenValue("test").header("alg", "RS256").subject("customer-123").audience(audience).build();
    }
}
