package com.supersports.catalog;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
class CatalogController {
    private final CatalogRepository repository;

    CatalogController(CatalogRepository repository) {
        this.repository = repository;
    }

    @GetMapping("/api/v1/catalog/status")
    Status status() {
        return new Status("catalog", "ready", repository.schemaVersion());
    }

    record Status(String service, String status, int schemaVersion) {}
}
