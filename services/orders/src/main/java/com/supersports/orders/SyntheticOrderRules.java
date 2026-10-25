package com.supersports.orders;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.HashSet;
import java.util.Set;
import java.util.UUID;

final class SyntheticOrderRules {
    static final int MAX_BATCH = 100;
    private SyntheticOrderRules() {}

    static void validate(SyntheticOrderImportController.OrderBatch batch, Instant now) {
        if (batch == null || batch.orders() == null || batch.orders().isEmpty() || batch.orders().size() > MAX_BATCH)
            throw new IllegalArgumentException("Order import batch must contain 1 to 100 orders");
        Set<String> sources = new HashSet<>();
        for (var order : batch.orders()) {
            if (order == null || order.sourceRef() == null || !order.sourceRef().matches("[A-Za-z0-9._:-]{8,120}") || !sources.add(order.sourceRef()))
                throw new IllegalArgumentException("Order source references must be valid and unique within a batch");
            try { UUID.fromString(order.customerSubject()); } catch (RuntimeException invalid) { throw new IllegalArgumentException("Customer subject must be a UUID"); }
            if (order.occurredAt() == null || order.occurredAt().isBefore(now.minus(365, ChronoUnit.DAYS)) || order.occurredAt().isAfter(now))
                throw new IllegalArgumentException("Synthetic order time must fall within the prior 365 days");
            if (order.currency() == null || !Set.of("INR", "USD").contains(order.currency())) throw new IllegalArgumentException("Unsupported currency");
            if (order.lines() == null || order.lines().isEmpty() || order.lines().size() > 5)
                throw new IllegalArgumentException("Synthetic orders require 1 to 5 item variations");
            if (order.addressSnapshot() == null || !"IN".equals(order.addressSnapshot().get("country")))
                throw new IllegalArgumentException("Synthetic customer address must be an Indian address snapshot");
            long lineSubtotal = 0;
            long lineDiscount = 0;
            Set<UUID> skus = new HashSet<>();
            for (var line : order.lines()) {
                if (line == null || line.quantity() != 1 || line.productTitle() == null || line.productTitle().isBlank() || line.productTitle().length() > 240)
                    throw new IllegalArgumentException("Each imported item must be one valid variation");
                try {
                    UUID sku = UUID.fromString(line.skuId()); UUID.fromString(line.productId());
                    if (!skus.add(sku)) throw new IllegalArgumentException("An order cannot repeat a SKU variation");
                } catch (RuntimeException invalid) { throw new IllegalArgumentException("Product and SKU identifiers must be UUIDs"); }
                if (!order.currency().equals(line.currency()) || line.unitPriceMinor() < 0 || line.discountMinor() < 0 || line.discountMinor() > line.unitPriceMinor())
                    throw new IllegalArgumentException("Order line money is invalid or mixes currencies");
                long expected = Math.subtractExact(line.unitPriceMinor(), line.discountMinor());
                if (line.lineTotalMinor() != expected) throw new IllegalArgumentException("Order line total does not reconcile");
                lineSubtotal = Math.addExact(lineSubtotal, line.unitPriceMinor());
                lineDiscount = Math.addExact(lineDiscount, line.discountMinor());
            }
            if (order.subtotalMinor() != lineSubtotal || order.discountMinor() != lineDiscount || order.discountMinor() > order.subtotalMinor())
                throw new IllegalArgumentException("Order subtotal or discount does not reconcile to its lines");
            if (order.taxMinor() < 0 || order.shippingMinor() < 0 || order.totalMinor() < 0 ||
                    order.totalMinor() != Math.addExact(Math.subtractExact(order.subtotalMinor(), order.discountMinor()),
                            Math.addExact(order.taxMinor(), order.shippingMinor())))
                throw new IllegalArgumentException("Order total does not reconcile");
        }
    }
}
