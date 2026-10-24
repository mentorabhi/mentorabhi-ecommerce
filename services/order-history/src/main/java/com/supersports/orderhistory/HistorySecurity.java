package com.supersports.orderhistory;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.boot.autoconfigure.condition.ConditionalOnWebApplication;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.web.SecurityFilterChain;
@Configuration @ConditionalOnWebApplication(type=ConditionalOnWebApplication.Type.SERVLET) class HistorySecurity {
 @Bean SecurityFilterChain historyChain(HttpSecurity http)throws Exception{return http.csrf(c->c.disable()).authorizeHttpRequests(a->a.requestMatchers("/actuator/health/**").permitAll().requestMatchers(HttpMethod.GET,"/api/v1/order-history/**").authenticated().anyRequest().denyAll()).oauth2ResourceServer(o->o.jwt(j->{})).build();}
}
