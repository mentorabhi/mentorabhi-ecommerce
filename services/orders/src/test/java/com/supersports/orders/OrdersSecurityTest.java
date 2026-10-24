package com.supersports.orders;
import jakarta.servlet.Filter;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.context.annotation.*;
import org.springframework.mock.web.MockServletContext;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.oauth2.jwt.*;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.context.support.AnnotationConfigWebApplicationContext;
import org.springframework.web.servlet.config.annotation.EnableWebMvc;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

class OrdersSecurityTest {
    AnnotationConfigWebApplicationContext context; MockMvc mvc;
    @BeforeEach void start(){context=new AnnotationConfigWebApplicationContext();context.setServletContext(new MockServletContext());context.register(Config.class);context.refresh();mvc=MockMvcBuilders.webAppContextSetup(context).addFilters(context.getBean("springSecurityFilterChain",Filter.class)).build();}
    @AfterEach void close(){context.close();}
    @Test void requiredAudienceRejectsOperatorRealmAccessTokens(){
        var validator=new OrdersSecurity().requiredAudience();
        var operator=Jwt.withTokenValue("operator").header("alg","none").claim("aud",java.util.List.of("supersports-api")).build();
        var customer=Jwt.withTokenValue("customer").header("alg","none").claim("aud",java.util.List.of("supersports-customer-api")).build();
        org.assertj.core.api.Assertions.assertThat(validator.validate(operator).hasErrors()).isTrue();
        org.assertj.core.api.Assertions.assertThat(validator.validate(customer).hasErrors()).isFalse();
    }
    @Test void orderRoutesRequireCustomerRealmAudienceAndAuthentication()throws Exception{
        mvc.perform(get("/api/v1/orders")).andExpect(status().isUnauthorized());
        mvc.perform(get("/api/v1/orders").header("Authorization","Bearer wrong-audience")).andExpect(status().isUnauthorized());
        mvc.perform(get("/api/v1/orders").header("Authorization","Bearer customer")).andExpect(status().isOk());
        mvc.perform(get("/api/v1/internal/checkout/worker").header("Authorization","Bearer customer")).andExpect(status().isForbidden());
    }
    @Configuration(proxyBeanMethods=false) @EnableWebSecurity @EnableWebMvc @Import(OrdersSecurity.class)
    static class Config{
        @Bean JwtDecoder jwtDecoder(){return token->{if(!"customer".equals(token))throw new BadJwtException("invalid test token");return Jwt.withTokenValue(token).header("alg","RS256").subject("customer-subject").claim("aud",java.util.List.of("supersports-customer-api")).build();};}
        @Bean Echo echo(){return new Echo();}
    }
    @RestController static class Echo{@RequestMapping("/api/**") String ok(){return "ok";}}
}
