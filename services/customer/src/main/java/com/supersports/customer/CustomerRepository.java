package com.supersports.customer;

import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
class CustomerRepository {
    private final JdbcTemplate jdbc;
    CustomerRepository(JdbcTemplate jdbc) { this.jdbc = jdbc; }

    Map<String, Object> profile(String subject) {
        jdbc.update("INSERT INTO customer_profile(subject) VALUES (?) ON CONFLICT DO NOTHING", subject);
        return jdbc.queryForMap("SELECT full_name AS \"fullName\", phone, line1, line2, city, state, postal_code AS \"postalCode\", country, revision FROM customer_profile WHERE subject=?", subject);
    }

    int saveProfile(String subject, CustomerRules.AddressInput p) {
        int changed = jdbc.update("UPDATE customer_profile SET full_name=?,phone=?,line1=?,line2=?,city=?,state=?,postal_code=?,country=?,revision=revision+1,updated_at=now() WHERE subject=? AND revision=?",
                p.fullName(), p.phone(), p.line1(), p.line2(), p.city(), p.state(), p.postalCode(), p.country(), subject, p.expectedRevision());
        if (changed == 0) {
            if (jdbc.queryForObject("SELECT count(*) FROM customer_profile WHERE subject=?", Integer.class, subject) == 0)
                throw new IllegalArgumentException("Customer profile must be loaded before it is updated");
            throw new StaleProfileException();
        }
        return p.expectedRevision() + 1;
    }

    List<Map<String, Object>> cart(String subject) {
        return jdbc.queryForList("SELECT sku_id AS \"skuId\", quantity, revision FROM cart_item WHERE subject=? ORDER BY created_at", subject);
    }

    Map<String, Object> setCartItem(String subject, UUID skuId, int quantity) {
        jdbc.update("INSERT INTO cart_item(subject,sku_id,quantity) VALUES (?,?,?) ON CONFLICT(subject,sku_id) DO UPDATE SET quantity=excluded.quantity,revision=cart_item.revision+CASE WHEN cart_item.quantity<>excluded.quantity THEN 1 ELSE 0 END,updated_at=now()",
                subject, skuId, quantity);
        return jdbc.queryForMap("SELECT sku_id AS \"skuId\", quantity, revision FROM cart_item WHERE subject=? AND sku_id=?", subject, skuId);
    }

    List<Map<String, Object>> wishlist(String subject) {
        return jdbc.queryForList("SELECT sku_id AS \"skuId\", created_at AS \"createdAt\" FROM wishlist_item WHERE subject=? ORDER BY created_at", subject);
    }

    void addWishlistItem(String subject, UUID skuId) {
        jdbc.update("INSERT INTO wishlist_item(subject,sku_id) VALUES (?,?) ON CONFLICT DO NOTHING", subject, skuId);
    }

    void removeWishlistItem(String subject, UUID skuId) {
        jdbc.update("DELETE FROM wishlist_item WHERE subject=? AND sku_id=?", subject, skuId);
    }

    void removeCartItem(String subject, UUID skuId) {
        jdbc.update("DELETE FROM cart_item WHERE subject=? AND sku_id=?", subject, skuId);
    }

    static final class StaleProfileException extends RuntimeException {}
}
