package com.supersports.orderhistory;

import java.io.IOException;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
class ConsumerCrashInjector {
    private final Path directory;

    @Autowired
    ConsumerCrashInjector(@Value("${order-history.fault-directory:/tmp/order-history-fault}") String directory) {
        this(Path.of(directory));
    }

    ConsumerCrashInjector(Path directory) {
        this.directory = directory;
    }

    void arm(UUID orderId) {
        try {
            Path armedDirectory = directory.resolve("armed");
            Path firedDirectory = directory.resolve("fired");
            Files.createDirectories(armedDirectory);
            if (Files.exists(firedDirectory.resolve(orderId.toString()))) {
                throw new IllegalStateException("The one-shot fault was already used for this order.");
            }
            Files.createFile(armedDirectory.resolve(orderId.toString()));
        } catch (IOException e) {
            throw new IllegalStateException("Could not arm the local one-shot consumer fault.", e);
        }
    }

    void armNextEvent() {
        try {
            Files.createDirectories(directory.resolve("armed"));
            Files.createFile(directory.resolve("armed").resolve("NEXT"));
        } catch (IOException e) {
            throw new IllegalStateException("Could not arm the local next-event consumer fault.", e);
        }
    }

    boolean consumeIfArmed(UUID orderId) {
        Path armed = directory.resolve("armed").resolve(orderId.toString());
        Path firedDirectory = directory.resolve("fired");
        try {
            if (!Files.exists(armed)) return false;
            Files.createDirectories(firedDirectory);
            Path fired = firedDirectory.resolve(orderId.toString());
            try {
                Files.move(armed, fired, StandardCopyOption.ATOMIC_MOVE);
            } catch (AtomicMoveNotSupportedException unsupported) {
                Files.move(armed, fired);
            }
            return true;
        } catch (java.nio.file.NoSuchFileException raced) {
            return false;
        } catch (IOException e) {
            throw new IllegalStateException("Could not consume the local one-shot consumer fault.", e);
        }
    }

    boolean consumeIfArmed(String orderId) {
        try {
            UUID parsed = UUID.fromString(orderId);
            if (consumeIfArmed(parsed)) return true;
            Path next = directory.resolve("armed").resolve("NEXT");
            if (!Files.exists(next)) return false;
            Path fired = directory.resolve("fired").resolve(parsed + "-" + UUID.randomUUID());
            Files.createDirectories(fired.getParent());
            try {
                Files.move(next, fired, StandardCopyOption.ATOMIC_MOVE);
            } catch (AtomicMoveNotSupportedException unsupported) {
                Files.move(next, fired);
            }
            return true;
        } catch (IllegalArgumentException | NullPointerException invalidKey) {
            return false;
        } catch (java.nio.file.NoSuchFileException raced) {
            return false;
        } catch (IOException e) {
            throw new IllegalStateException("Could not consume the local next-event consumer fault.", e);
        }
    }
}
