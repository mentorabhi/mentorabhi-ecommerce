package com.supersports.orderhistory;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class ConsumerCrashInjectorTest {
    @TempDir Path directory;

    @Test
    void consumesOnlyTheMatchingOneShotRequest() throws Exception {
        UUID orderId = UUID.randomUUID();
        ConsumerCrashInjector injector = new ConsumerCrashInjector(directory);
        injector.arm(orderId);

        assertFalse(injector.consumeIfArmed(UUID.randomUUID()));
        assertTrue(injector.consumeIfArmed(orderId));
        assertFalse(injector.consumeIfArmed(orderId));
        assertTrue(Files.exists(directory.resolve("fired").resolve(orderId.toString())));
    }

    @Test
    void nextEventRequestIsConsumedByOneValidOrderOnly() throws Exception {
        ConsumerCrashInjector injector = new ConsumerCrashInjector(directory);
        injector.armNextEvent();

        assertFalse(injector.consumeIfArmed("not-an-order-id"));
        String orderId = UUID.randomUUID().toString();
        assertTrue(injector.consumeIfArmed(orderId));
        assertFalse(injector.consumeIfArmed(UUID.randomUUID().toString()));
        injector.armNextEvent();
        assertTrue(injector.consumeIfArmed(orderId));
        try (var files = Files.list(directory.resolve("fired"))) {
            assertTrue(files.count() == 2);
        }
    }
}
