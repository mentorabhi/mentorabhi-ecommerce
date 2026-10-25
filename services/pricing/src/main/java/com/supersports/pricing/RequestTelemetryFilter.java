package com.supersports.pricing;

import java.io.IOException;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;
import org.springframework.web.servlet.HandlerMapping;

/** Safe request metadata only. Console exceptions are not exported to the request-log stream. */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE + 10)
final class RequestTelemetryFilter extends OncePerRequestFilter {
    private static final Logger REQUESTS = LoggerFactory.getLogger("supersports.http");

    @Override protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
                                               FilterChain chain) throws ServletException, IOException {
        long started = System.nanoTime();
        boolean failed = true;
        try {
            chain.doFilter(request, response);
            failed = false;
        } finally {
            Object pattern = request.getAttribute(HandlerMapping.BEST_MATCHING_PATTERN_ATTRIBUTE);
            String route = pattern == null ? "UNMATCHED" : pattern.toString();
            if (route.length() > 240 || !route.matches("[a-zA-Z0-9_/{}/.*:-]+")) route = "UNMATCHED";
            String method = request.getMethod();
            if (!java.util.Set.of("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS").contains(method)) method = "OTHER";
            try (var a = MDC.putCloseable("http.route", route);
                 var b = MDC.putCloseable("http.request.method", method);
                 var c = MDC.putCloseable("http.response.status_code", Integer.toString(failed ? 500 : response.getStatus()));
                 var d = MDC.putCloseable("elapsed_ms", Long.toString((System.nanoTime() - started) / 1_000_000))) {
                REQUESTS.info("http_request");
            }
        }
    }
}
