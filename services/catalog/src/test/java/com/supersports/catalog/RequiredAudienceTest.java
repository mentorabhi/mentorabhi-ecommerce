package com.supersports.catalog;

import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.security.oauth2.jwt.Jwt;
import static org.assertj.core.api.Assertions.assertThat;

class RequiredAudienceTest {
    @Test void requiresApiAudienceEvenIfOtherAudiencesArePresent() {
        var validator = new SecurityConfiguration().requiredApiAudience();
        var token = Jwt.withTokenValue("test").header("alg", "RS256").subject("customer");
        assertThat(validator.validate(token.build()).hasErrors()).isTrue();
        assertThat(validator.validate(token.audience(List.of("account")).build()).hasErrors()).isTrue();
        assertThat(validator.validate(token.audience(List.of("account", "supersports-api")).build()).hasErrors()).isFalse();
    }
}
