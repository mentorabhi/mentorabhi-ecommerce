package com.supersports.catalog;

import java.util.List;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

@Repository
class CatalogRepository {
    private final JdbcTemplate jdbc;

    CatalogRepository(JdbcTemplate jdbc) { this.jdbc = jdbc; }

    int schemaVersion() {
        return jdbc.queryForObject("SELECT max(version::integer) FROM flyway_schema_history WHERE success", Integer.class);
    }

    List<Map<String, Object>> sports() {
        return jdbc.queryForList("SELECT id, slug, name, active, revision FROM sports WHERE active ORDER BY name");
    }

    List<Map<String, Object>> categories() {
        return jdbc.query("SELECT id, sport_id AS \"sportId\", parent_id AS \"parentId\", slug, name, attributes::text AS attributes, active, revision FROM categories WHERE active ORDER BY name", (rs,n) -> {var row=new LinkedHashMap<String,Object>();row.put("id",rs.getObject("id"));row.put("sportId",rs.getObject("sportId"));row.put("parentId",rs.getObject("parentId"));row.put("slug",rs.getString("slug"));row.put("name",rs.getString("name"));row.put("attributes",Json.read(rs.getString("attributes")));row.put("active",rs.getBoolean("active"));row.put("revision",rs.getInt("revision"));return row;});
    }

    List<Map<String, Object>> products(boolean activeOnly) {
        String query="SELECT p.id,p.category_id AS \"categoryId\",p.slug,p.brand,p.title,p.description,p.status,p.revision,COALESCE(jsonb_agg(jsonb_build_object('id',s.id,'code',s.code,'attributes',s.attributes,'assetKey',s.asset_key,'altText',s.alt_text)) FILTER (WHERE s.id IS NOT NULL),'[]'::jsonb)::text AS skus FROM products p LEFT JOIN skus s ON s.product_id=p.id AND s.active "+(activeOnly?"WHERE p.status='active' ":"")+"GROUP BY p.id ORDER BY p.title";
        return jdbc.query(query,(rs,n)->{var row=new LinkedHashMap<String,Object>();for(String field:List.of("id","categoryId","slug","brand","title","description","status","revision"))row.put(field,rs.getObject(field));row.put("skus",Json.read(rs.getString("skus")));return row;});
    }

    List<Map<String, Object>> searchProducts(String query, String category) {
        String search = query == null || query.isBlank() ? null : query.trim();
        String selectedCategory = category == null || category.isBlank() ? null : category.trim();
        return jdbc.query("SELECT p.id,p.category_id AS \"categoryId\",p.slug,p.brand,p.title,p.description,p.status,p.revision,COALESCE(jsonb_agg(jsonb_build_object('id',s.id,'code',s.code,'attributes',s.attributes,'assetKey',s.asset_key,'altText',s.alt_text)) FILTER (WHERE s.id IS NOT NULL),'[]'::jsonb)::text AS skus FROM products p JOIN categories c ON c.id=p.category_id LEFT JOIN skus s ON s.product_id=p.id AND s.active WHERE p.status='active' AND c.active AND (CAST(? AS text) IS NULL OR p.title ILIKE '%'||?||'%' OR p.brand ILIKE '%'||?||'%' OR p.description ILIKE '%'||?||'%' OR c.name ILIKE '%'||?||'%' OR c.slug ILIKE '%'||?||'%') AND (CAST(? AS text) IS NULL OR c.id::text=? OR c.slug=?) GROUP BY p.id ORDER BY p.title LIMIT 100",
                (rs,n)->{var row=new LinkedHashMap<String,Object>();for(String field:List.of("id","categoryId","slug","brand","title","description","status","revision"))row.put(field,rs.getObject(field));row.put("skus",Json.read(rs.getString("skus")));return row;},
                search,search,search,search,search,search,selectedCategory,selectedCategory,selectedCategory);
    }

    Map<String,Object> publicSku(UUID id) {
        return jdbc.queryForObject("SELECT s.id,(s.active AND p.status='active' AND c.active) AS active FROM skus s JOIN products p ON p.id=s.product_id JOIN categories c ON c.id=p.category_id WHERE s.id=?", (rs,n)->Map.of("id",rs.getObject("id"),"active",rs.getBoolean("active")), id);
    }

    Map<String,Object> skuStatus(UUID id) {
        return jdbc.queryForMap("SELECT s.id, (s.active AND p.status='active') AS active FROM skus s JOIN products p ON p.id=s.product_id WHERE s.id=?", id);
    }

    UUID createSport(String slug, String name, String actor) {
        UUID id=jdbc.queryForObject("INSERT INTO sports(id,slug,name) VALUES (?,?,?) ON CONFLICT(slug) DO UPDATE SET name=excluded.name,revision=sports.revision+CASE WHEN sports.name IS DISTINCT FROM excluded.name THEN 1 ELSE 0 END RETURNING id",UUID.class,UUID.randomUUID(),slug,name);
        return id;
    }

    UUID createCategory(UUID sportId, UUID parentId, String slug, String name, Object attributes, String actor) {
        UUID id;
        if (parentId != null && jdbc.queryForObject("SELECT count(*) FROM categories WHERE id=? AND sport_id=? AND active", Integer.class, parentId, sportId) == 0)
            throw new IllegalArgumentException("Parent category must be active and belong to the same sport");
        Integer activeProducts=jdbc.queryForObject("SELECT count(*) FROM products p JOIN categories c ON c.id=p.category_id WHERE c.sport_id=? AND c.slug=? AND p.status='active'",Integer.class,sportId,slug);
        Integer existing=jdbc.queryForObject("SELECT count(*) FROM categories WHERE sport_id=? AND slug=? AND attributes::text<>?",Integer.class,sportId,slug,Json.write(attributes));
        if(activeProducts>0&&existing>0)throw new IllegalArgumentException("Category schema cannot change while active products use it");
        id=jdbc.queryForObject("INSERT INTO categories(id,sport_id,parent_id,slug,name,attributes) VALUES (?,?,?,?,?,?::jsonb) ON CONFLICT(sport_id,slug) DO UPDATE SET parent_id=excluded.parent_id,name=excluded.name,attributes=excluded.attributes,revision=categories.revision+CASE WHEN (categories.parent_id,categories.name,categories.attributes) IS DISTINCT FROM (excluded.parent_id,excluded.name,excluded.attributes) THEN 1 ELSE 0 END RETURNING id",UUID.class,UUID.randomUUID(),sportId,parentId,slug,name,Json.write(attributes));
        return id;
    }

    UUID createProduct(UUID categoryId, String slug, String brand, String title, String description, String actor) {
        UUID id=jdbc.queryForObject("INSERT INTO products(id,category_id,slug,brand,title,description) VALUES (?,?,?,?,?,?) ON CONFLICT(slug) DO UPDATE SET category_id=excluded.category_id,brand=excluded.brand,title=excluded.title,description=excluded.description,revision=products.revision+CASE WHEN (products.category_id,products.brand,products.title,products.description) IS DISTINCT FROM (excluded.category_id,excluded.brand,excluded.title,excluded.description) THEN 1 ELSE 0 END,updated_at=CASE WHEN (products.category_id,products.brand,products.title,products.description) IS DISTINCT FROM (excluded.category_id,excluded.brand,excluded.title,excluded.description) THEN now() ELSE products.updated_at END RETURNING id",UUID.class,UUID.randomUUID(),categoryId,slug,brand,title,description);
        return id;
    }

    UUID createSku(UUID productId, String code, Object attributes, String assetKey, String altText, String actor) {
        if (!assetKey.matches("[a-zA-Z0-9/_-]+\\.svg") || assetKey.startsWith("/") || assetKey.contains(".."))
            throw new IllegalArgumentException("assetKey must be a relative local SVG key");
        if (jdbc.queryForObject("SELECT count(*) FROM products WHERE id=? AND status='draft'", Integer.class, productId) != 1)
            throw new IllegalArgumentException("SKUs can only be added to draft products");
        UUID id=jdbc.queryForObject("INSERT INTO skus(id,product_id,code,attributes,asset_key,alt_text) VALUES (?,?,?,?::jsonb,?,?) ON CONFLICT(code) DO UPDATE SET attributes=excluded.attributes,asset_key=excluded.asset_key,alt_text=excluded.alt_text,revision=skus.revision+CASE WHEN (skus.attributes,skus.asset_key,skus.alt_text) IS DISTINCT FROM (excluded.attributes,excluded.asset_key,excluded.alt_text) THEN 1 ELSE 0 END WHERE skus.product_id=excluded.product_id RETURNING id",UUID.class,UUID.randomUUID(),productId,code,Json.write(attributes),assetKey,altText);
        if(id==null)throw new IllegalArgumentException("SKU code already belongs to another product");
        return id;
    }

    List<UUID> skuIds(UUID productId) {
        return jdbc.query("SELECT id FROM skus WHERE product_id=? AND active ORDER BY id", (rs, row) -> rs.getObject(1, UUID.class), productId);
    }

    @Transactional
    void activate(UUID productId, int expectedRevision, String actor) {
        var product = jdbc.queryForMap("SELECT category_id,status,revision FROM products WHERE id=? FOR UPDATE", productId);
        int revision = (Integer) product.get("revision");
        if (revision != expectedRevision) throw new StaleRevisionException();
        if (!"draft".equals(product.get("status"))) throw new IllegalArgumentException("Only draft products can be activated");
        if (jdbc.queryForObject("SELECT count(*) FROM skus WHERE product_id=? AND active", Integer.class, productId) == 0)
            throw new IllegalArgumentException("At least one active SKU is required");
        jdbc.update("UPDATE products SET status='active',revision=revision+1,updated_at=now() WHERE id=?", productId);
        audit("product", productId, "activate", actor, revision, revision + 1, Map.of());
    }

    private void audit(String type, UUID id, String action, String actor, Integer from, int to, Object details) {
        jdbc.update("INSERT INTO catalog_audit(entity_type,entity_id,action,actor,from_revision,to_revision,details) VALUES (?,?,?,?,?,?,?::jsonb)", type, id, action, actor, from, to, Json.write(details));
    }
}
