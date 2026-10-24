package com.supersports.configuration;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

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
    @PutMapping("/api/v1/configuration/checkout/{key}")
    ConfigurationRepository.SettingUpdate update(@PathVariable String key,@RequestBody SettingInput input,@AuthenticationPrincipal Jwt jwt){
        try{return repository.updateCheckoutSetting(key,input.value(),input.expectedRevision(),jwt.getSubject());}
        catch(ConfigurationRepository.StaleConfigurationException e){throw new ResponseStatusException(HttpStatus.CONFLICT,"Configuration changed; refresh and retry");}
        catch(IllegalArgumentException e){throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,e.getMessage());}
    }
    record SettingInput(String value,long expectedRevision){}
}
