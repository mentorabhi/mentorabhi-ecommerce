package com.supersports.customer;

import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/v1/customer")
class CustomerController {
    private final CustomerRepository repository;
    private final RestClient catalog;

    CustomerController(CustomerRepository repository, @Value("${catalog.base-url}") String catalogUrl) {
        this.repository = repository;
        this.catalog = RestClient.builder().baseUrl(catalogUrl).build();
    }

    @GetMapping("/profile") Map<String, Object> profile(@AuthenticationPrincipal Jwt jwt) {
        return repository.profile(subject(jwt));
    }

    @PutMapping("/profile") Map<String, Object> saveProfile(@AuthenticationPrincipal Jwt jwt, @RequestBody CustomerRules.AddressInput input) {
        try {
            var address = CustomerRules.validateAddress(input);
            int revision = repository.saveProfile(subject(jwt), address);
            return Map.of("revision", revision);
        } catch (CustomerRepository.StaleProfileException e) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "Profile changed; refresh and try again");
        } catch (IllegalArgumentException e) {
            throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY, e.getMessage());
        }
    }

    @GetMapping("/cart") List<Map<String, Object>> cart(@AuthenticationPrincipal Jwt jwt) {
        return repository.cart(subject(jwt));
    }

    @PutMapping("/cart/items/{skuId}") Map<String, Object> setCartItem(@AuthenticationPrincipal Jwt jwt,
            @PathVariable UUID skuId, @RequestBody QuantityInput input) {
        try {
            requireActiveSku(skuId);
            return repository.setCartItem(subject(jwt), skuId, CustomerRules.quantity(input.quantity()));
        } catch (IllegalArgumentException e) {
            throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY, e.getMessage());
        } catch (RestClientException e) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "Catalog validation unavailable");
        }
    }

    @DeleteMapping("/cart/items/{skuId}") @ResponseStatus(HttpStatus.NO_CONTENT)
    void removeCartItem(@AuthenticationPrincipal Jwt jwt, @PathVariable UUID skuId) {
        repository.removeCartItem(subject(jwt), skuId);
    }

    @GetMapping("/wishlist") List<Map<String, Object>> wishlist(@AuthenticationPrincipal Jwt jwt) {
        return repository.wishlist(subject(jwt));
    }

    @PostMapping("/wishlist/items/{skuId}") @ResponseStatus(HttpStatus.NO_CONTENT)
    void addWishlistItem(@AuthenticationPrincipal Jwt jwt, @PathVariable UUID skuId) {
        try {
            requireActiveSku(skuId);
            repository.addWishlistItem(subject(jwt), skuId);
        } catch (IllegalArgumentException e) {
            throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY, e.getMessage());
        } catch (RestClientException e) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "Catalog validation unavailable");
        }
    }

    @DeleteMapping("/wishlist/items/{skuId}") @ResponseStatus(HttpStatus.NO_CONTENT)
    void removeWishlistItem(@AuthenticationPrincipal Jwt jwt, @PathVariable UUID skuId) {
        repository.removeWishlistItem(subject(jwt), skuId);
    }

    private void requireActiveSku(UUID skuId) {
        try {
            var status = catalog.get().uri("/api/v1/catalog/public/skus/{id}", skuId).retrieve().body(PublicSku.class);
            if (status == null || !status.active()) throw new IllegalArgumentException("Choose an active product variant");
        } catch (org.springframework.web.client.HttpClientErrorException.NotFound e) {
            throw new IllegalArgumentException("Choose an active product variant");
        }
    }

    private static String subject(Jwt jwt) { return jwt.getSubject(); }
    record QuantityInput(int quantity) {}
    record PublicSku(UUID id, boolean active) {}
}
