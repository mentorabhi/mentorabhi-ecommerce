package com.supersports.catalog;

import java.util.Arrays;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.security.oauth2.jwt.Jwt;
import static org.assertj.core.api.Assertions.assertThat;

class RealmRolesConverterTest {
    private final RealmRolesConverter converter = new RealmRolesConverter();

    private Jwt token(Object realmAccess) {
        var builder = Jwt.withTokenValue("unit-test").header("alg", "RS256").subject("customer");
        if (realmAccess != null) builder.claim("realm_access", realmAccess);
        return builder.build();
    }

    @Test void mapsRealmRolesOnlyAndDeduplicates() {
        var jwt = Jwt.withTokenValue("unit-test").header("alg", "RS256").subject("customer")
                .claim("scope", "platform-admin")
                .claim("resource_access", Map.of("client", Map.of("roles", List.of("platform-admin"))))
                .claim("realm_access", Map.of("roles", List.of("customer", "catalog-admin", "customer")))
                .build();
        assertThat(converter.convert(jwt)).extracting("authority")
                .containsExactly("ROLE_customer", "ROLE_catalog-admin");
    }

    @Test void missingRealmAccessGrantsNoRoles() {
        assertThat(converter.convert(token(null))).isEmpty();
    }

    @Test void malformedRealmAccessGrantsNoRoles() {
        for (Object claim : List.of("customer", 12, List.of("customer"))) {
            assertThat(converter.convert(token(claim))).isEmpty();
        }
    }

    @Test void missingOrNonListRolesGrantNoRoles() {
        for (Object claim : List.of(Map.of(), Map.of("roles", "customer"), Map.of("roles", 12))) {
            assertThat(converter.convert(token(claim))).isEmpty();
        }
    }

    @Test void malformedRoleListFailsClosedAsAWhole() {
        for (var roles : List.of(List.of("customer", 12), List.of("customer", ""),
                List.of("customer", " "), Arrays.asList("customer", null))) {
            assertThat(converter.convert(token(Map.of("roles", roles)))).isEmpty();
        }
    }

    @Test void emptyRolesGrantNoRoles() {
        assertThat(converter.convert(token(Map.of("roles", List.of())))).isEmpty();
    }
}
