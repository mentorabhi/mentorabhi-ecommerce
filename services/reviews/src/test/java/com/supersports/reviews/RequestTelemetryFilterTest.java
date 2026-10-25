package com.supersports.reviews;

import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.AppenderBase;
import jakarta.servlet.ServletException;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.slf4j.LoggerFactory;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.web.servlet.HandlerMapping;
import static org.junit.jupiter.api.Assertions.*;

class RequestTelemetryFilterTest {
    @Test void recordsTemplateInsteadOfSubmittedPathBodyAndQueryEvenOnFailure() {
        Logger logger = (Logger) LoggerFactory.getLogger("supersports.http");
        List<ILoggingEvent> events = new ArrayList<>();
        var appender = new AppenderBase<ILoggingEvent>() {
            @Override protected void append(ILoggingEvent event) {
                event.prepareForDeferredProcessing(); events.add(event);
            }
        };
        appender.start(); logger.addAppender(appender);
        try {
            var request = new MockHttpServletRequest("POST", "/private-address-sentinel");
            request.setQueryString("password=secret-sentinel");
            request.setContent("address-sentinel".getBytes(java.nio.charset.StandardCharsets.UTF_8));
            request.setAttribute(HandlerMapping.BEST_MATCHING_PATTERN_ATTRIBUTE, "/products/{id}");
            var response = new MockHttpServletResponse();
            assertThrows(ServletException.class, () -> new RequestTelemetryFilter().doFilter(request, response,
                (req, res) -> { throw new ServletException("exception-secret-sentinel"); }));
            assertEquals(1, events.size());
            var event = events.getFirst();
            assertEquals("http_request", event.getFormattedMessage());
            assertEquals("/products/{id}", event.getMDCPropertyMap().get("http.route"));
            assertEquals("500", event.getMDCPropertyMap().get("http.response.status_code"));
            assertFalse(event.getMDCPropertyMap().toString().contains("sentinel"));
            assertNull(event.getThrowableProxy());
        } finally { logger.detachAppender(appender); appender.stop(); }
    }
}
