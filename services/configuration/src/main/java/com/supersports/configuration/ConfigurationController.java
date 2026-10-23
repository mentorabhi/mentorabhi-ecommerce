package com.supersports.configuration;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
class ConfigurationController {
    private final ConfigurationRepository repository;

    ConfigurationController(ConfigurationRepository repository) {
        this.repository = repository;
    }

    @GetMapping("/api/v1/configuration")
    ConfigurationSnapshot configuration() {
        return repository.read();
    }
}
