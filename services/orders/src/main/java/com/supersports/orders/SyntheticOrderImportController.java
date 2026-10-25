package com.supersports.orders;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/v1/admin/synthetic-orders")
class SyntheticOrderImportController {
    private final SyntheticOrderRepository repository;
    private final boolean enabled;
    SyntheticOrderImportController(SyntheticOrderRepository repository,
            @Value("${supersports.synthetic-import.enabled:false}") boolean enabled) {
        this.repository = repository; this.enabled = enabled;
    }

    @PostMapping("/batch") Map<String,Object> importBatch(@RequestBody OrderBatch batch, @AuthenticationPrincipal Jwt jwt) {
        if (!enabled) throw new ResponseStatusException(HttpStatus.NOT_FOUND);
        Map<String,Object> realmAccess = jwt == null ? null : jwt.getClaim("realm_access");
        if (jwt == null || !"supersports-demo-seeder".equals(jwt.getClaimAsString("preferred_username"))
                || realmAccess == null || !(realmAccess.get("roles") instanceof List<?> roles)
                || !roles.contains("supersports-synthetic-seeder"))
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Synthetic order seeder identity required");
        try {
            SyntheticOrderRules.validate(batch, Instant.now());
            var imported = repository.importBatch(batch.orders());
            long created = imported.stream().filter(row -> Boolean.FALSE.equals(row.get("replayed"))).count();
            return Map.of("accepted", imported.size(), "created", created, "replayed", imported.size() - created, "orders", imported);
        } catch (IllegalArgumentException | ArithmeticException invalid) {
            throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY, invalid.getMessage());
        } catch (IllegalStateException conflict) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, conflict.getMessage());
        }
    }

    record OrderBatch(List<OrderFixture> orders) {}
    record OrderFixture(String sourceRef, String customerSubject, Instant occurredAt, String currency,
                        long subtotalMinor, long discountMinor, long taxMinor, long shippingMinor, long totalMinor,
                        Map<String,Object> addressSnapshot, List<OrderLineFixture> lines) {}
    record OrderLineFixture(String skuId, String productId, String productTitle, int quantity,
                            long unitPriceMinor, long discountMinor, long lineTotalMinor, String currency) {}
}
