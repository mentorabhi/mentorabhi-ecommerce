package com.supersports.fulfillment;
import java.util.List;
import jakarta.servlet.DispatcherType;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.authorization.AuthorizationManager;
import org.springframework.security.web.access.intercept.RequestAuthorizationContext;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.oauth2.core.OAuth2TokenValidator;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.jwt.JwtClaimNames;
import org.springframework.security.oauth2.jwt.JwtClaimValidator;

@Configuration(proxyBeanMethods=false)
class FulfillmentSecurity {
 private AuthorizationManager<RequestAuthorizationContext> scope(){return(a,c)->{var x=a.get();String required="POST".equals(c.getRequest().getMethod())?"checkout:fulfillment.schedule":"checkout:fulfillment.status";return new org.springframework.security.authorization.AuthorizationDecision(x instanceof JwtAuthenticationToken t&&t.getToken().getAudience().contains("supersports-checkout-internal-api")&&"supersports-checkout-worker".equals(t.getToken().getClaimAsString("azp"))&&t.getAuthorities().stream().anyMatch(v->v.getAuthority().equals("SCOPE_"+required)));};}
 @Bean OAuth2TokenValidator<Jwt> audience(){return new JwtClaimValidator<List<String>>(JwtClaimNames.AUD,a->a!=null&&a.contains("supersports-checkout-internal-api"));}
 @Bean SecurityFilterChain chain(HttpSecurity h)throws Exception{return h.csrf(AbstractHttpConfigurer::disable).sessionManagement(s->s.sessionCreationPolicy(SessionCreationPolicy.STATELESS)).authorizeHttpRequests(a->a.dispatcherTypeMatchers(DispatcherType.ERROR).permitAll().requestMatchers("/actuator/health/liveness","/actuator/health/readiness").permitAll().requestMatchers("/api/v1/internal/checkout/fulfillment/**").access(scope()).anyRequest().denyAll()).oauth2ResourceServer(o->o.jwt(Customizer.withDefaults())).build();}
}
