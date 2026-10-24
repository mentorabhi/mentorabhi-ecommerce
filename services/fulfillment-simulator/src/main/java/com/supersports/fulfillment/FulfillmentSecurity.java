package com.supersports.fulfillment;

import java.util.List;
import jakarta.servlet.DispatcherType;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.authorization.AuthorizationManager;
import org.springframework.security.authorization.AuthorizationDecision;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.Authentication;
import org.springframework.security.oauth2.core.OAuth2TokenValidator;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.access.intercept.RequestAuthorizationContext;

@Configuration(proxyBeanMethods=false)
class FulfillmentSecurity {
    private AuthorizationManager<RequestAuthorizationContext> checkoutScope(){
        return (authentication,context)->{
            Authentication current=authentication.get();
            String path=context.getRequest().getRequestURI();
            String required="GET".equals(context.getRequest().getMethod())?"checkout:fulfillment.status":
                path.endsWith("/cancel-claim")||path.endsWith("/cancel-finalize")?"checkout:fulfillment.cancel":"checkout:fulfillment.schedule";
            boolean allowed=current instanceof JwtAuthenticationToken token
                &&token.getToken().getAudience().contains("supersports-checkout-internal-api")
                &&"supersports-checkout-worker".equals(token.getToken().getClaimAsString("azp"))
                &&token.getAuthorities().stream().anyMatch(authority->authority.getAuthority().equals("SCOPE_"+required));
            return new AuthorizationDecision(allowed);
        };
    }

    private AuthorizationManager<RequestAuthorizationContext> operatorAudience(){
        return (authentication,context)->{
            Authentication current=authentication.get();
            return new AuthorizationDecision(current instanceof JwtAuthenticationToken token
                &&token.getToken().getAudience().contains("supersports-api"));
        };
    }

    @Bean OAuth2TokenValidator<Jwt> audience(){
        return jwt->{
            List<String> audiences=jwt.getAudience();
            boolean operator=audiences!=null&&audiences.contains("supersports-api");
            boolean checkout=audiences!=null&&audiences.contains("supersports-checkout-internal-api")
                &&"supersports-checkout-worker".equals(jwt.getClaimAsString("azp"));
            return operator||checkout?org.springframework.security.oauth2.core.OAuth2TokenValidatorResult.success()
                :org.springframework.security.oauth2.core.OAuth2TokenValidatorResult.failure(new org.springframework.security.oauth2.core.OAuth2Error("invalid_token","Required API audience or checkout client is missing",null));
        };
    }

    @Bean SecurityFilterChain chain(HttpSecurity http)throws Exception{
        return http.csrf(AbstractHttpConfigurer::disable)
            .sessionManagement(session->session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(authorize->authorize.dispatcherTypeMatchers(DispatcherType.ERROR).permitAll()
                .requestMatchers("/actuator/health/liveness","/actuator/health/readiness").permitAll()
                .requestMatchers("/api/v1/internal/checkout/fulfillment/**").access(checkoutScope())
                .requestMatchers("/api/v1/operator/shipments/**").access(operatorAudience())
                .anyRequest().denyAll())
            .oauth2ResourceServer(resource->resource.jwt(Customizer.withDefaults())).build();
    }
}
