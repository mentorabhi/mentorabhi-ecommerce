package com.supersports.pricing;

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
import org.springframework.security.oauth2.jwt.JwtClaimNames;
import org.springframework.security.oauth2.jwt.JwtClaimValidator;
import org.springframework.security.authorization.AuthorizationManager;
import org.springframework.security.web.access.intercept.RequestAuthorizationContext;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.security.web.SecurityFilterChain;

@Configuration(proxyBeanMethods = false)
class PricingSecurity {
    private static AuthorizationManager<RequestAuthorizationContext> operatorAudience(){return (authentication,context)->{var auth=authentication.get();boolean allowed=auth instanceof JwtAuthenticationToken token&&token.getToken().getAudience().contains("supersports-api");return new org.springframework.security.authorization.AuthorizationDecision(allowed);};}
    private static AuthorizationManager<RequestAuthorizationContext> checkoutScope(String scope){return (authentication,context)->{var auth=authentication.get();boolean allowed=auth instanceof JwtAuthenticationToken token&&token.getToken().getAudience().contains("supersports-checkout-internal-api")&&"supersports-checkout-worker".equals(token.getToken().getClaimAsString("azp"))&&token.getAuthorities().stream().anyMatch(a->a.getAuthority().equals("SCOPE_"+scope));return new org.springframework.security.authorization.AuthorizationDecision(allowed);};}
    @Bean
    OAuth2TokenValidator<Jwt> requiredAudience() {
        return jwt->{List<String> audiences=jwt.getAudience();boolean operator=audiences!=null&&audiences.contains("supersports-api");boolean checkout=audiences!=null&&audiences.contains("supersports-checkout-internal-api")&&"supersports-checkout-worker".equals(jwt.getClaimAsString("azp"));return operator||checkout?org.springframework.security.oauth2.core.OAuth2TokenValidatorResult.success():org.springframework.security.oauth2.core.OAuth2TokenValidatorResult.failure(new org.springframework.security.oauth2.core.OAuth2Error("invalid_token","Required API audience or checkout client is missing",null));};
    }

    @Bean
    SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        return http
                .csrf(AbstractHttpConfigurer::disable)
                .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(authorize -> authorize
                        .dispatcherTypeMatchers(DispatcherType.ERROR).permitAll()
                        .requestMatchers(HttpMethod.GET, "/actuator/health/liveness", "/actuator/health/readiness").permitAll()
                        .requestMatchers(HttpMethod.POST,"/api/v1/internal/checkout/pricing/quotes").access(checkoutScope("checkout:pricing.quote"))
                        .requestMatchers(HttpMethod.POST,"/api/v1/internal/checkout/pricing/coupon-holds").access(checkoutScope("checkout:pricing.coupon.hold"))
                        .requestMatchers(HttpMethod.POST,"/api/v1/internal/checkout/pricing/coupon-holds/*/protect").access(checkoutScope("checkout:pricing.coupon.protect"))
                        .requestMatchers(HttpMethod.POST,"/api/v1/internal/checkout/pricing/coupon-holds/*/commit").access(checkoutScope("checkout:pricing.coupon.commit"))
                        .requestMatchers(HttpMethod.POST,"/api/v1/internal/checkout/pricing/coupon-holds/*/release").access(checkoutScope("checkout:pricing.coupon.release"))
                        .requestMatchers("/api/v1/internal/checkout/**").denyAll()
                        .requestMatchers(HttpMethod.GET, "/api/v1/pricing/currency", "/api/v1/pricing/public/skus", "/api/v1/pricing/public/skus/**").permitAll()
                        .requestMatchers(HttpMethod.GET, "/api/v1/pricing/prices", "/api/v1/pricing/coupons").access(operatorAudience())
                        .requestMatchers(HttpMethod.POST, "/api/v1/pricing/**").access(operatorAudience())
                        .requestMatchers(HttpMethod.PUT, "/api/v1/pricing/**").access(operatorAudience())
                        .anyRequest().denyAll())
                .oauth2ResourceServer(oauth -> oauth.jwt(Customizer.withDefaults()))
                .build();
    }
}
