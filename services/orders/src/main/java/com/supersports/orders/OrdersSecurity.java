package com.supersports.orders;
import java.util.List;
import jakarta.servlet.DispatcherType;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.oauth2.core.OAuth2TokenValidator;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.jwt.JwtClaimNames;
import org.springframework.security.oauth2.jwt.JwtClaimValidator;
import org.springframework.security.web.SecurityFilterChain;

@Configuration(proxyBeanMethods=false)
class OrdersSecurity {
    @Bean OAuth2TokenValidator<Jwt> requiredAudience(){return new JwtClaimValidator<List<String>>(JwtClaimNames.AUD,aud->aud!=null&&aud.contains("supersports-customer-api"));}
    @Bean SecurityFilterChain securityFilterChain(HttpSecurity http)throws Exception{
        return http.csrf(AbstractHttpConfigurer::disable).sessionManagement(s->s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(a->a.dispatcherTypeMatchers(DispatcherType.ERROR).permitAll().requestMatchers("/actuator/health/liveness","/actuator/health/readiness").permitAll().requestMatchers("/api/v1/orders/**","/api/v1/admin/synthetic-orders/**").authenticated().anyRequest().denyAll())
                .oauth2ResourceServer(o->o.jwt(Customizer.withDefaults())).build();
    }
}
