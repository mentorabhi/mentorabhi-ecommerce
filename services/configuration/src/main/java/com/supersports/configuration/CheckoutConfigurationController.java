package com.supersports.configuration;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController @RequestMapping("/api/v1/internal/checkout/configuration")
class CheckoutConfigurationController {
    private final ConfigurationRepository repository;
    CheckoutConfigurationController(ConfigurationRepository repository){this.repository=repository;}
    @GetMapping ConfigurationRepository.CheckoutSettings settings(){return repository.checkoutSettings();}
    @GetMapping("/returns-policy") ConfigurationRepository.ReturnPolicy returnsPolicy(){return repository.returnsPolicy();}
}
