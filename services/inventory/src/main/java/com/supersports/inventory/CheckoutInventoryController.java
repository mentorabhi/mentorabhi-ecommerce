package com.supersports.inventory;

import java.time.Instant;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/v1/internal/checkout/inventory/reservations")
class CheckoutInventoryController {
    private final InventoryRepository repository;
    CheckoutInventoryController(InventoryRepository repository) { this.repository = repository; }

    @PostMapping @org.springframework.transaction.annotation.Transactional
    Map<String,Object> reserve(@RequestBody ReservationRequest request) {
        try {
            UUID orderId=UUID.fromString(request.orderId());repository.acceptCheckoutFence(orderId,request.fence());
            var lines = new HashMap<UUID,Long>();
            for (var line : request.lines()) if (lines.put(UUID.fromString(line.skuId()), line.quantity()) != null)
                throw new IllegalArgumentException("Duplicate SKU");
            return repository.reserve(orderId, lines, Instant.parse(request.expiresAt()));
        } catch (InventoryRepository.StaleCheckoutFenceException e) { throw new ResponseStatusException(HttpStatus.CONFLICT,"Stale checkout fence");
        } catch (InventoryRepository.InsufficientStockException e) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "Insufficient available stock");
        } catch (IllegalArgumentException e) {
            throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY, e.getMessage());
        }
    }
    @PostMapping("/{orderId}/protect") @org.springframework.transaction.annotation.Transactional Map<String,Object> protect(@PathVariable UUID orderId,@RequestHeader("X-Checkout-Fence")long fence) { return transition(orderId,fence,"PROTECTED"); }
    @PostMapping("/{orderId}/commit") @org.springframework.transaction.annotation.Transactional Map<String,Object> commit(@PathVariable UUID orderId,@RequestHeader("X-Checkout-Fence")long fence) { return transition(orderId,fence,"COMMITTED"); }
    @PostMapping("/{orderId}/release") @org.springframework.transaction.annotation.Transactional Map<String,Object> release(@PathVariable UUID orderId,@RequestHeader("X-Checkout-Fence")long fence) { return transition(orderId,fence,"RELEASED"); }
    private Map<String,Object> transition(UUID id,long fence,String state) {
        try { repository.acceptCheckoutFence(id,fence);return repository.transitionReservation(id,state); }
        catch (InventoryRepository.StaleCheckoutFenceException e) { throw new ResponseStatusException(HttpStatus.CONFLICT,"Stale checkout fence"); }
        catch (InventoryRepository.ReservationNotFoundException e) { throw new ResponseStatusException(HttpStatus.NOT_FOUND,"Reservation not found"); }
        catch (IllegalStateException e) { throw new ResponseStatusException(HttpStatus.CONFLICT,e.getMessage()); }
    }
    record ReservationRequest(String orderId,String expiresAt,List<ReservationLine> lines,long fence) {}
    record ReservationLine(String skuId,long quantity) {}
}
