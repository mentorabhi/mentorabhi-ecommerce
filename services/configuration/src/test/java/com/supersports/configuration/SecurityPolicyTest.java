package com.supersports.configuration;

import jakarta.servlet.Filter;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.context.annotation.*;
import org.springframework.http.HttpMethod;
import org.springframework.mock.web.MockServletContext;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.oauth2.jwt.*;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.context.support.AnnotationConfigWebApplicationContext;
import org.springframework.web.servlet.config.annotation.EnableWebMvc;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

class SecurityPolicyTest {
    private AnnotationConfigWebApplicationContext context;
    private MockMvc mvc;

    @BeforeEach void start() {
        context = new AnnotationConfigWebApplicationContext();
        context.setServletContext(new MockServletContext());
        context.register(TestConfiguration.class);
        context.refresh();
        mvc = MockMvcBuilders.webAppContextSetup(context)
                .addFilters(context.getBean("springSecurityFilterChain", Filter.class)).build();
    }
    @AfterEach void close() { context.close(); }

    @Test void validIdentityWithoutRoleClaimsCanUseSupportedAdminMethods() throws Exception {
        mvc.perform(request(HttpMethod.GET, "/api/v1/configuration").header("Authorization", "Bearer valid"))
                .andExpect(status().isOk());
    }
    @Test void anonymousRequestsRequireSignIn() throws Exception {
        mvc.perform(get("/api/v1/configuration")).andExpect(status().isUnauthorized());
    }
    @Test void invalidTokenIsRejected() throws Exception {
        mvc.perform(get("/api/v1/configuration").header("Authorization", "Bearer invalid"))
                .andExpect(status().isUnauthorized());
    }
    @Test void unsupportedMethodsStayDenied() throws Exception {
        mvc.perform(delete("/api/v1/configuration").header("Authorization", "Bearer valid"))
                .andExpect(status().isForbidden());
    }
    @Test void healthRemainsPublic() throws Exception {
        mvc.perform(get("/actuator/health/readiness")).andExpect(status().isOk());
    }
    @Test void checkoutWorkerCanReadOnlyItsScopedInternalConfiguration() throws Exception {
        mvc.perform(get("/api/v1/internal/checkout/configuration").header("Authorization","Bearer valid")).andExpect(status().isForbidden());
        mvc.perform(get("/api/v1/internal/checkout/configuration").header("Authorization","Bearer worker")).andExpect(status().isOk());
        mvc.perform(get("/api/v1/configuration").header("Authorization","Bearer worker")).andExpect(status().isForbidden());
    }

    @Configuration(proxyBeanMethods = false)
    @EnableWebSecurity
    @EnableWebMvc
    @Import(SecurityConfiguration.class)
    static class TestConfiguration {
        @Bean JwtDecoder jwtDecoder() {
            // Isolate route policy from cryptography; live tests cover signed and tampered tokens.
            return token -> {
                if (!java.util.Set.of("valid","worker").contains(token)) throw new BadJwtException("Invalid test token");
                if(token.equals("worker"))return Jwt.withTokenValue(token).header("alg","RS256").subject("checkout").claim("aud",java.util.List.of("supersports-checkout-internal-api")).claim("azp","supersports-checkout-worker").claim("scope","checkout:configuration.read").build();
                return Jwt.withTokenValue(token).header("alg", "RS256")
                        .subject("ordinary-local-user").claim("aud", java.util.List.of("supersports-api")).build();
            };
        }
        @Bean EchoController echoController() { return new EchoController(); }
    }
    @RestController
    static class EchoController {
        @RequestMapping({"/api/**", "/actuator/health/readiness"})
        String ok() { return "ok"; }
    }
}
