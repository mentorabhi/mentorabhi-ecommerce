package com.supersports.pricing;

import java.time.Instant;
import java.sql.Timestamp;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

@Repository
class PricingRepository {
    private final JdbcTemplate jdbc;
    PricingRepository(JdbcTemplate jdbc) { this.jdbc = jdbc; }

    Map<String,Object> currency() { return jdbc.queryForMap("SELECT code,revision FROM store_currency WHERE id=1"); }
    Map<String,Object> publicSkuPrice(UUID skuId) { return jdbc.queryForMap("SELECT p.sku_id AS \"skuId\",p.currency,p.amount_minor AS \"amountMinor\" FROM sku_price p JOIN store_currency c ON c.code=p.currency AND c.id=1 WHERE p.sku_id=?", skuId); }
    List<Map<String,Object>> prices() { return jdbc.queryForList("SELECT sku_id AS \"skuId\",currency,amount_minor AS \"amountMinor\",revision FROM sku_price ORDER BY sku_id,currency"); }

    @Transactional
    int setPrice(UUID sku, String currency, long amount, int expectedRevision, String actor) {
        if (amount <= 0) throw new IllegalArgumentException("amountMinor must be positive");
        if (jdbc.queryForObject("SELECT count(*) FROM currency_registry WHERE code=? AND enabled", Integer.class, currency) != 1)
            throw new IllegalArgumentException("Unsupported currency");
        String lockKey=sku+":"+currency;
        jdbc.query("SELECT pg_advisory_xact_lock(hashtextextended(?,0))",ps->ps.setString(1,lockKey),rs->{rs.next();return null;});
        var existing = jdbc.queryForList("SELECT revision,amount_minor FROM sku_price WHERE sku_id=? AND currency=? FOR UPDATE", sku, currency);
        int actual = existing.isEmpty() ? 0 : ((Number) existing.getFirst().get("revision")).intValue();
        if (actual != expectedRevision) throw new StalePriceException();
        if (!existing.isEmpty() && ((Number) existing.getFirst().get("amount_minor")).longValue() == amount) return actual;
        jdbc.update("INSERT INTO sku_price(sku_id,currency,amount_minor,revision) VALUES (?,?,?,1) ON CONFLICT(sku_id,currency) DO UPDATE SET amount_minor=excluded.amount_minor,revision=sku_price.revision+1,updated_at=now()", sku, currency, amount);
        int revision = jdbc.queryForObject("SELECT revision FROM sku_price WHERE sku_id=? AND currency=?", Integer.class, sku, currency);
        jdbc.update("INSERT INTO price_audit(sku_id,currency,amount_minor,actor,revision) VALUES (?,?,?,?,?)", sku, currency, amount, actor, revision);
        return revision;
    }

    @Transactional
    Map<String,Object> activateCurrency(String code, int expectedRevision) {
        if (jdbc.queryForObject("SELECT count(*) FROM currency_registry WHERE code=? AND enabled", Integer.class, code) != 1)
            throw new IllegalArgumentException("Unsupported currency");
        if (jdbc.queryForObject("SELECT count(*) FROM (SELECT sku_id FROM sku_price GROUP BY sku_id HAVING count(DISTINCT currency)<2) incomplete", Integer.class) > 0)
            throw new IllegalArgumentException("All known SKUs must have INR and USD prices");
        int changed=jdbc.update("UPDATE store_currency SET code=?,revision=revision+1 WHERE id=1 AND revision=?",code,expectedRevision);
        if(changed!=1)throw new StalePriceException();
        return currency();
    }

    boolean complete(List<UUID> skuIds) {
        if (skuIds == null || skuIds.isEmpty() || skuIds.stream().distinct().count() != skuIds.size()) return false;
        String marks=String.join(",",Collections.nCopies(skuIds.size(),"?"));
        return jdbc.queryForObject("SELECT count(*) FROM sku_price WHERE sku_id IN ("+marks+") AND currency IN ('INR','USD') AND amount_minor>0",Integer.class,skuIds.toArray())==2*skuIds.size();
    }

    List<Map<String,Object>> coupons() {
        return jdbc.queryForList("SELECT id,code,active,starts_at AS \"startsAt\",ends_at AS \"endsAt\",currency,kind,value,minimum_subtotal_minor AS \"minimumSubtotalMinor\",maximum_discount_minor AS \"maximumDiscountMinor\",global_limit AS \"globalLimit\",per_customer_limit AS \"perCustomerLimit\",rules,revision FROM coupon ORDER BY code");
    }

    UUID createCoupon(CouponInput c) {
        UUID id=UUID.randomUUID();
        jdbc.update("INSERT INTO coupon(id,code,active,starts_at,ends_at,currency,kind,value,minimum_subtotal_minor,maximum_discount_minor,global_limit,per_customer_limit,rules) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?::jsonb)",id,c.code().trim().toUpperCase(),c.active(),Timestamp.from(Instant.parse(c.startsAt())),Timestamp.from(Instant.parse(c.endsAt())),c.currency().toUpperCase(),c.kind().toUpperCase(),c.value(),c.minimumSubtotalMinor(),c.maximumDiscountMinor(),c.globalLimit(),c.perCustomerLimit(),Json.write(c.rules()==null?Map.of():c.rules()));
        return id;
    }

    record CouponInput(String code,boolean active,String startsAt,String endsAt,String currency,String kind,long value,long minimumSubtotalMinor,Long maximumDiscountMinor,Long globalLimit,Integer perCustomerLimit,Map<String,Object> rules) {}
}
