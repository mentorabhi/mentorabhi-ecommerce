package com.supersports.catalog;

import java.util.Map;
import java.util.UUID;
import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.*;
import org.springframework.http.ResponseEntity;

@RestController
@RequestMapping("/api/v1/catalog/products")
class CatalogMutationController {
    private final CatalogRepository repository;
    CatalogMutationController(CatalogRepository repository) { this.repository=repository; }

    @PutMapping("/{id}") Map<String,Object> update(@PathVariable UUID id,@RequestBody Update input,@AuthenticationPrincipal Jwt jwt) {
        return repository.updateProduct(id,input.expectedRevision(),input.idempotencyKey(),jwt.getSubject(),input.brand(),input.title(),input.description(),input.details());
    }
    @PostMapping("/{id}/retire") Map<String,Object> retire(@PathVariable UUID id,@RequestBody Retirement input,@AuthenticationPrincipal Jwt jwt) {
        return repository.retireProduct(id,input.expectedRevision(),input.idempotencyKey(),jwt.getSubject(),input.reason());
    }
    @ExceptionHandler(StaleRevisionException.class) ResponseEntity<Map<String,String>> stale() { return error(HttpStatus.CONFLICT,"Product revision is stale"); }
    @ExceptionHandler(EmptyResultDataAccessException.class) ResponseEntity<Map<String,String>> missing() { return error(HttpStatus.NOT_FOUND,"Product not found"); }
    @ExceptionHandler(IllegalArgumentException.class) ResponseEntity<Map<String,String>> invalid(IllegalArgumentException e) { return error(HttpStatus.UNPROCESSABLE_ENTITY,e.getMessage()); }
    private static ResponseEntity<Map<String,String>> error(HttpStatus status,String message) { return ResponseEntity.status(status).body(Map.of("error",message)); }
    record Update(int expectedRevision,String idempotencyKey,String brand,String title,String description,ProductDetails details) {}
    record Retirement(int expectedRevision,String idempotencyKey,String reason) {}
}
