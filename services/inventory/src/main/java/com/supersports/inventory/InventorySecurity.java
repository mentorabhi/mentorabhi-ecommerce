package com.supersports.inventory;

import java.util.List;
import jakarta.servlet.DispatcherType;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.oauth2.core.OAuth2TokenValidator;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.authorization.AuthorizationManager;
import org.springframework.security.web.access.intercept.RequestAuthorizationContext;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.security.web.SecurityFilterChain;

@Configuration(proxyBeanMethods = false)
class InventorySecurity {
    private static AuthorizationManager<RequestAuthorizationContext> checkoutScope(String scope) {
        return (authentication, context) -> {
            var auth = authentication.get();
            if (!(auth instanceof JwtAuthenticationToken token)) return new org.springframework.security.authorization.AuthorizationDecision(false);
            Jwt jwt = token.getToken();
            boolean allowed = jwt.getAudience().contains("supersports-checkout-internal-api")
                    && "supersports-checkout-worker".equals(jwt.getClaimAsString("azp"))
                    && token.getAuthorities().stream().anyMatch(a -> a.getAuthority().equals("SCOPE_" + scope));
            return new org.springframework.security.authorization.AuthorizationDecision(allowed);
        };
    }
    private static AuthorizationManager<RequestAuthorizationContext> operatorAudience(){return (authentication,context)->{var auth=authentication.get();boolean allowed=auth instanceof JwtAuthenticationToken token&&token.getToken().getAudience().contains("supersports-api");return new org.springframework.security.authorization.AuthorizationDecision(allowed);};}
    @Bean
    OAuth2TokenValidator<Jwt> requiredAudience() {
        return jwt -> {
            List<String> audiences = jwt.getAudience();
            if (audiences == null) return org.springframework.security.oauth2.core.OAuth2TokenValidatorResult.failure(new org.springframework.security.oauth2.core.OAuth2Error("invalid_token","Required API audience is missing",null));
            if (audiences.contains("supersports-api")) return org.springframework.security.oauth2.core.OAuth2TokenValidatorResult.success();
            boolean internal = audiences.contains("supersports-checkout-internal-api")
                    && "supersports-checkout-worker".equals(jwt.getClaimAsString("azp"));
            return internal ? org.springframework.security.oauth2.core.OAuth2TokenValidatorResult.success()
                    : org.springframework.security.oauth2.core.OAuth2TokenValidatorResult.failure(new org.springframework.security.oauth2.core.OAuth2Error("invalid_token","Required API audience or checkout client is missing",null));
        };
    }

    @Bean
    SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        return http
                .csrf(AbstractHttpConfigurer::disable)
                .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(authorize -> authorize
                        .dispatcherTypeMatchers(DispatcherType.ERROR).permitAll()
                        .requestMatchers(HttpMethod.GET, "/actuator/health/liveness", "/actuator/health/readiness").permitAll()
                        .requestMatchers(HttpMethod.GET, "/api/v1/inventory/availability/**").permitAll()
                        .requestMatchers(HttpMethod.POST, "/api/v1/internal/checkout/inventory/reservations").access(checkoutScope("checkout:inventory.reserve"))
                        .requestMatchers(HttpMethod.POST, "/api/v1/internal/checkout/inventory/reservations/*/protect").access(checkoutScope("checkout:inventory.protect"))
                        .requestMatchers(HttpMethod.POST, "/api/v1/internal/checkout/inventory/reservations/*/commit").access(checkoutScope("checkout:inventory.commit"))
                        .requestMatchers(HttpMethod.POST, "/api/v1/internal/checkout/inventory/reservations/*/release").access(checkoutScope("checkout:inventory.release"))
                        .requestMatchers(HttpMethod.POST, "/api/v1/internal/checkout/inventory/reservations/*/cancel").access(checkoutScope("checkout:inventory.cancel"))
                        .requestMatchers(HttpMethod.POST, "/api/v1/internal/checkout/inventory/returns/*/receive").access(checkoutScope("checkout:inventory.return.receive"))
                        .requestMatchers("/api/v1/internal/checkout/**").denyAll()
                        .requestMatchers(HttpMethod.GET, "/api/v1/inventory/**").access(operatorAudience())
                        .requestMatchers(HttpMethod.POST, "/api/v1/inventory/**").access(operatorAudience())
                        .anyRequest().denyAll())
                .oauth2ResourceServer(oauth -> oauth.jwt(Customizer.withDefaults()))
                .build();
    }
}
