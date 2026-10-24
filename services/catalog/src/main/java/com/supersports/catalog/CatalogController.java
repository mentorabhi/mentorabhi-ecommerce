package com.supersports.catalog;

import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

@RestController
@RequestMapping("/api/v1/catalog")
class CatalogController {
    private final CatalogRepository repository;
    private final RestClient pricing;
    CatalogController(CatalogRepository repository, @Value("${pricing.base-url}") String pricingUrl) { this.repository = repository; pricing=RestClient.builder().baseUrl(pricingUrl).build(); }

    @GetMapping("/status") Status status() { return new Status("catalog", "ready", repository.schemaVersion()); }
    @GetMapping("/sports") List<Map<String,Object>> sports() { return repository.sports(); }
    @GetMapping("/categories") List<Map<String,Object>> categories() { return repository.categories(); }
    @GetMapping("/products") List<Map<String,Object>> products() { return repository.products(true); }
    @GetMapping("/admin/products") List<Map<String,Object>> allProducts() { return repository.products(false); }
    @GetMapping("/skus/{skuId}/status") Map<String,Object> skuStatus(@PathVariable UUID skuId) { return repository.skuStatus(skuId); }

    @PostMapping("/sports") Map<String,Object> createSport(@RequestBody SportInput input, @AuthenticationPrincipal Jwt jwt) {
        return Map.of("id", repository.createSport(required(input.slug(), "slug"), required(input.name(), "name"), actor(jwt)));
    }

    @PostMapping("/categories") Map<String,Object> createCategory(@RequestBody CategoryInput input, @AuthenticationPrincipal Jwt jwt) {
        return Map.of("id", repository.createCategory(UUID.fromString(input.sportId()), input.parentId() == null ? null : UUID.fromString(input.parentId()), required(input.slug(), "slug"), required(input.name(), "name"), input.attributes() == null ? List.of() : input.attributes(), actor(jwt)));
    }

    @PostMapping("/products") Map<String,Object> createProduct(@RequestBody ProductInput input, @AuthenticationPrincipal Jwt jwt) {
        return Map.of("id", repository.createProduct(UUID.fromString(input.categoryId()), required(input.slug(), "slug"), required(input.brand(), "brand"), required(input.title(), "title"), required(input.description(), "description"), actor(jwt)));
    }

    @PostMapping("/products/{productId}/skus") Map<String,Object> createSku(@PathVariable UUID productId, @RequestBody SkuInput input, @AuthenticationPrincipal Jwt jwt) {
        return Map.of("id", repository.createSku(productId, required(input.code(), "code"), input.attributes() == null ? Map.of() : input.attributes(), required(input.assetKey(), "assetKey"), required(input.altText(), "altText"), actor(jwt)));
    }

    @PostMapping("/products/{productId}/activate") Map<String,Object> activate(@PathVariable UUID productId, @RequestBody ActivationInput input, @AuthenticationPrincipal Jwt jwt) {
        try {
            var result=pricing.post().uri("/api/v1/pricing/completeness").header(HttpHeaders.AUTHORIZATION,"Bearer "+jwt.getTokenValue()).body(Map.of("skuIds",repository.skuIds(productId))).retrieve().body(Completeness.class);
            if(result==null||!result.complete())throw new ResponseStatusException(HttpStatus.CONFLICT,"Every active SKU needs INR and USD prices before activation");
            repository.activate(productId, input.expectedRevision(), actor(jwt)); return Map.of("status", "active", "revision", input.expectedRevision() + 1);
        }
        catch (StaleRevisionException e) { throw new ResponseStatusException(HttpStatus.CONFLICT, "Product revision is stale"); }
        catch (IllegalArgumentException e) { throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY, e.getMessage()); }
        catch (RestClientException e) { throw new ResponseStatusException(HttpStatus.BAD_GATEWAY,"Pricing completeness check unavailable"); }
    }

    private static String required(String value, String field) {
        if (value == null || value.isBlank()) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, field + " is required");
        return value.trim();
    }
    private static String actor(Jwt jwt) { return jwt == null ? "system" : jwt.getSubject(); }

    record Status(String service, String status, int schemaVersion) {}
    record SportInput(String slug, String name) {}
    record CategoryInput(String sportId, String parentId, String slug, String name, List<Map<String,Object>> attributes) {}
    record ProductInput(String categoryId, String slug, String brand, String title, String description) {}
    record SkuInput(String code, Map<String,Object> attributes, String assetKey, String altText) {}
    record ActivationInput(int expectedRevision) {}
    record Completeness(boolean complete) {}
}
