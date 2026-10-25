package com.supersports.orders;

import static org.assertj.core.api.Assertions.*;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.server.ResponseStatusException;

class SyntheticOrderRulesTest {
    final Instant now = Instant.parse("2026-10-24T12:00:00Z");
    SyntheticOrderImportController.OrderFixture order(String currency, Instant at, long total) {
        var line = new SyntheticOrderImportController.OrderLineFixture("00000000-0000-4000-8000-000000000001", "00000000-0000-4000-8000-000000000002", "Demo bat", 1, 1000, 0, 1000, currency);
        return new SyntheticOrderImportController.OrderFixture("demo-20261024-0001", "00000000-0000-4000-8000-000000000003", at, currency, 1000, 0, 180, 99, total, Map.of("country","IN"), List.of(line));
    }
    @Test void validDatedOrderReconcilesAndSerializes() {
        var order = order("INR", now.minusSeconds(3600), 1279);
        assertThatCode(() -> SyntheticOrderRules.validate(new SyntheticOrderImportController.OrderBatch(List.of(order)),now)).doesNotThrowAnyException();
        assertThat(OrdersJson.write(order)).contains("2026-10-24");
    }
    @Test void rejectsWrongTotalCurrencyDatesAndDuplicateSources() {
        for (var order : List.of(order("INR",now,1278),order("EUR",now,1279),order("INR",now.plusSeconds(1),1279),order("INR",now.minusSeconds(366L*86400),1279))) {
            assertThatThrownBy(() -> SyntheticOrderRules.validate(new SyntheticOrderImportController.OrderBatch(List.of(order)),now)).isInstanceOf(IllegalArgumentException.class);
        }
        var valid = order("INR",now,1279);
        assertThatThrownBy(() -> SyntheticOrderRules.validate(new SyntheticOrderImportController.OrderBatch(List.of(valid,valid)),now)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SyntheticOrderRules.validate(new SyntheticOrderImportController.OrderBatch(java.util.Collections.nCopies(101,valid)),now)).isInstanceOf(IllegalArgumentException.class);
    }
    @Test void disabledRouteAndSelfRegisteredSeederNameDoNotGrantImport() {
        var jwt = Jwt.withTokenValue("test").header("alg","none").subject("test").claim("preferred_username","supersports-demo-seeder").build();
        assertThatThrownBy(() -> new SyntheticOrderImportController(null,false).importBatch(null,jwt)).isInstanceOfSatisfying(ResponseStatusException.class,e -> assertThat(e.getStatusCode().value()).isEqualTo(404));
        assertThatThrownBy(() -> new SyntheticOrderImportController(null,true).importBatch(null,jwt)).isInstanceOfSatisfying(ResponseStatusException.class,e -> assertThat(e.getStatusCode().value()).isEqualTo(403));
    }
}
