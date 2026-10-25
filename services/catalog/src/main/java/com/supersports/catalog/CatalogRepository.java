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

    private static final String PUBLIC_FROM = " FROM products p JOIN categories c ON c.id=p.category_id JOIN sports sp ON sp.id=c.sport_id ";
    private static final String VISIBLE = " p.status='active' AND c.active AND sp.active ";
    private static final String PUBLIC_SELECT = "SELECT p.id,p.category_id AS \"categoryId\",c.sport_id AS \"sportId\",p.slug,p.brand,p.title,p.description,p.status,p.revision,p.details::text AS details,"
            + "COALESCE((SELECT jsonb_agg(jsonb_build_object('id',s.id,'code',s.code,'attributes',s.attributes,'assetKey',s.asset_key,'altText',s.alt_text) ORDER BY s.code,s.id) FROM skus s WHERE s.product_id=p.id AND s.active),'[]'::jsonb)::text AS skus";
    private static final RowMapper<Map<String,Object>> PUBLIC_ROW = (rs,n) -> {
        var row=new LinkedHashMap<String,Object>();
        for(String field:List.of("id","categoryId","sportId","slug","brand","title","description","status","revision")) row.put(field,rs.getObject(field));
        row.put("details",Json.read(rs.getString("details")));
        row.put("skus",Json.read(rs.getString("skus")));
        return row;
    };

    Map<String,Object> browse(int page,int pageSize,String search,String category,String sport) {
        var args=new java.util.ArrayList<Object>();
        StringBuilder where=new StringBuilder(" WHERE "+VISIBLE);
        CatalogSearch query=search==null ? null : CatalogSearch.parse(search);
        String searchable="to_tsvector('simple',concat_ws(' ',p.title,p.brand,p.details->>'model',p.description,c.name,sp.name))";
        if(query!=null) {
            if(query.noMatch()) where.append(" AND false");
            else if(query.literal()!=null) {
                where.append(" AND strpos(lower(concat_ws(' ',p.title,p.brand,p.description,c.name)),lower(?))>0");
                args.add(query.literal());
            } else {
                if(query.equipment()!=null) {
                    where.append(" AND (p.details->>'equipmentType' ~* ? OR (coalesce(p.details->>'equipmentType','')='' AND p.title ~* ?))");
                    args.add(query.equipmentWords().replace("\\m", "^").replace("\\M", "$")); args.add(query.equipmentWords());
                }
                if(!query.terms().isEmpty()) {
                    where.append(" AND "+searchable+" @@ plainto_tsquery('simple',?)"); args.add(query.terms());
                }
            }
        }
        if(category!=null) { where.append(" AND (c.id::text=? OR c.slug=?)"); args.add(category); args.add(category); }
        if(sport!=null) { where.append(" AND (sp.id::text=? OR sp.slug=?)"); args.add(sport); args.add(sport); }
        long total=jdbc.queryForObject("SELECT count(*)"+PUBLIC_FROM+where,Long.class,args.toArray());
        String order="p.title,p.id";
        if(query!=null && !query.noMatch()) {
            order="ts_rank_cd(setweight(to_tsvector('simple',coalesce(p.title,'')),'A') || "
                    +"setweight(to_tsvector('simple',concat_ws(' ',p.brand,p.details->>'model')),'B') || "
                    +"setweight(to_tsvector('simple',coalesce(p.description,'')),'D'),plainto_tsquery('simple',?)) DESC,"+order;
            args.add(query.rankingTerms());
        }
        args.add(pageSize); args.add((page-1)*pageSize);
        var items=jdbc.query(PUBLIC_SELECT+PUBLIC_FROM+where+" ORDER BY "+order+" LIMIT ? OFFSET ?",PUBLIC_ROW,args.toArray());
        return Map.of("items",items,"page",page,"pageSize",pageSize,"total",total,"hasNext",(long)page*pageSize<total);
    }

    Map<String,Object> productBySlug(String slug) {
        return jdbc.queryForObject(PUBLIC_SELECT+PUBLIC_FROM+" WHERE "+VISIBLE+" AND p.slug=?",PUBLIC_ROW,slug);
    }

    List<Map<String,Object>> productsForSkus(List<UUID> ids) {
        return jdbc.query(PUBLIC_SELECT+PUBLIC_FROM+" WHERE "+VISIBLE
                +" AND EXISTS (SELECT 1 FROM skus saved WHERE saved.product_id=p.id AND saved.active AND saved.id IN ("
                +String.join(",",java.util.Collections.nCopies(ids.size(),"?"))+")) ORDER BY p.title,p.id",PUBLIC_ROW,ids.toArray());
    }

    List<Map<String,Object>> similar(String slug,int limit) {
        var source=productBySlug(slug);
        @SuppressWarnings("unchecked") var details=(Map<String,Object>)source.get("details");
        String equipment=(String)details.getOrDefault("equipmentType","");
        return jdbc.query(PUBLIC_SELECT+PUBLIC_FROM+" WHERE "+VISIBLE+" AND p.id<>? ORDER BY "
                +"CASE WHEN ?<>'' AND p.details->>'equipmentType'=? AND c.sport_id=? THEN 0 WHEN c.sport_id=? THEN 1 WHEN ?<>'' AND p.details->>'equipmentType'=? THEN 2 ELSE 3 END, p.title,p.id LIMIT ?",
                PUBLIC_ROW,source.get("id"),equipment,equipment,source.get("sportId"),source.get("sportId"),equipment,equipment,limit);
    }

    @Transactional
    Map<String,Object> updateProduct(UUID id,int expectedRevision,String key,String actor,String brand,String title,String description,ProductDetails details) {
        ProductDetails.text(brand,"brand",120,true); ProductDetails.text(title,"title",200,true); ProductDetails.text(description,"description",10000,true);
        if(details==null) throw new IllegalArgumentException("details is required");
        details.validated();
        return mutate(id,expectedRevision,key,actor,"update",Map.of("brand",brand,"title",title,"description",description,"details",details));
    }

    @Transactional
    Map<String,Object> retireProduct(UUID id,int expectedRevision,String key,String actor,String reason) {
        ProductDetails.text(reason,"reason",500,true);
        return mutate(id,expectedRevision,key,actor,"retire",Map.of("reason",reason));
    }

    @SuppressWarnings("unchecked")
    private Map<String,Object> mutate(UUID id,int expectedRevision,String key,String actor,String operation,Map<String,Object> changes) {
        if(expectedRevision<1 || key==null || !key.matches("[A-Za-z0-9._:-]{8,120}")) throw new IllegalArgumentException("Positive expectedRevision and idempotencyKey of 8..120 safe characters required");
        String request=Json.write(Map.of("id",id,"expectedRevision",expectedRevision,"operation",operation,"changes",changes));
        jdbc.query("SELECT pg_advisory_xact_lock(hashtextextended(?,0))",ps->ps.setString(1,key),rs->{rs.next();return null;});
        var prior=jdbc.queryForList("SELECT actor,request=?::jsonb AS same,response::text AS response FROM catalog_mutations WHERE idempotency_key=?",request,key);
        if(!prior.isEmpty()) {
            var previous=prior.getFirst();
            if(!actor.equals(previous.get("actor")) || !Boolean.TRUE.equals(previous.get("same")))
                throw new org.springframework.web.server.ResponseStatusException(org.springframework.http.HttpStatus.CONFLICT,"Idempotency key already used with a different request or actor");
            return (Map<String,Object>)Json.read((String)previous.get("response"));
        }
        var product=jdbc.queryForMap("SELECT revision,status FROM products WHERE id=? FOR UPDATE",id);
        int revision=((Number)product.get("revision")).intValue();
        if(revision!=expectedRevision) throw new StaleRevisionException();
        if("retired".equals(product.get("status"))) throw new IllegalArgumentException("Retired products cannot be changed");
        String status=(String)product.get("status");
        if(operation.equals("retire")) {
            status="retired";
            jdbc.update("UPDATE products SET status='retired',revision=revision+1,updated_at=now() WHERE id=?",id);
        } else {
            if ("active".equals(status)) requirePhotographicSkus(id);
            jdbc.update("UPDATE products SET brand=?,title=?,description=?,details=?::jsonb,revision=revision+1,updated_at=now() WHERE id=?",changes.get("brand"),changes.get("title"),changes.get("description"),Json.write(changes.get("details")),id);
        }
        var result=Map.<String,Object>of("id",id.toString(),"status",status,"revision",revision+1);
        audit("product",id,operation,actor,revision,revision+1,changes);
        jdbc.update("INSERT INTO catalog_mutations(idempotency_key,actor,request,response) VALUES (?,?,?::jsonb,?::jsonb)",key,actor,request,Json.write(result));
        return result;
    }

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
        String query="SELECT p.id,p.category_id AS \"categoryId\",p.slug,p.brand,p.title,p.description,p.status,p.revision,p.details::text AS details,COALESCE(jsonb_agg(jsonb_build_object('id',s.id,'code',s.code,'attributes',s.attributes,'assetKey',s.asset_key,'altText',s.alt_text)) FILTER (WHERE s.id IS NOT NULL),'[]'::jsonb)::text AS skus FROM products p LEFT JOIN skus s ON s.product_id=p.id AND s.active "+(activeOnly?"WHERE p.status='active' ":"")+"GROUP BY p.id ORDER BY p.title";
        return jdbc.query(query,(rs,n)->{var row=new LinkedHashMap<String,Object>();for(String field:List.of("id","categoryId","slug","brand","title","description","status","revision"))row.put(field,rs.getObject(field));row.put("details",Json.read(rs.getString("details")));row.put("skus",Json.read(rs.getString("skus")));return row;});
    }

    List<Map<String, Object>> searchProducts(String query, String category) {
        String search = query == null || query.isBlank() ? null : query.trim();
        String selectedCategory = category == null || category.isBlank() ? null : category.trim();
        return jdbc.query("SELECT p.id,p.category_id AS \"categoryId\",p.slug,p.brand,p.title,p.description,p.status,p.revision,p.details::text AS details,COALESCE(jsonb_agg(jsonb_build_object('id',s.id,'code',s.code,'attributes',s.attributes,'assetKey',s.asset_key,'altText',s.alt_text)) FILTER (WHERE s.id IS NOT NULL),'[]'::jsonb)::text AS skus FROM products p JOIN categories c ON c.id=p.category_id LEFT JOIN skus s ON s.product_id=p.id AND s.active WHERE p.status='active' AND c.active AND (CAST(? AS text) IS NULL OR p.title ILIKE '%'||?||'%' OR p.brand ILIKE '%'||?||'%' OR p.description ILIKE '%'||?||'%' OR c.name ILIKE '%'||?||'%' OR c.slug ILIKE '%'||?||'%') AND (CAST(? AS text) IS NULL OR c.id::text=? OR c.slug=?) GROUP BY p.id ORDER BY p.title LIMIT 100",
                (rs,n)->{var row=new LinkedHashMap<String,Object>();for(String field:List.of("id","categoryId","slug","brand","title","description","status","revision"))row.put(field,rs.getObject(field));row.put("details",Json.read(rs.getString("details")));row.put("skus",Json.read(rs.getString("skus")));return row;},
                search,search,search,search,search,search,selectedCategory,selectedCategory,selectedCategory);
    }

    Map<String,Object> publicSku(UUID id) {
        return jdbc.queryForObject("SELECT s.id,(s.active AND p.status='active' AND c.active) AS active FROM skus s JOIN products p ON p.id=s.product_id JOIN categories c ON c.id=p.category_id WHERE s.id=?", (rs,n)->Map.of("id",rs.getObject("id"),"active",rs.getBoolean("active")), id);
    }

    Map<String,Object> skuStatus(UUID id) {
        return jdbc.queryForMap("SELECT s.id, (s.active AND p.status='active') AS active FROM skus s JOIN products p ON p.id=s.product_id WHERE s.id=?", id);
    }

    Map<String,Object> checkoutSku(UUID id) {
        return jdbc.queryForMap("SELECT s.id AS \"skuId\",s.active AND p.status='active' AND c.active AS active,p.id AS \"productId\",p.title,c.id AS \"categoryId\",c.slug AS \"categorySlug\",s.revision AS \"skuRevision\",p.revision AS \"productRevision\",c.revision AS \"categoryRevision\" FROM skus s JOIN products p ON p.id=s.product_id JOIN categories c ON c.id=p.category_id WHERE s.id=?",id);
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
        UUID id=jdbc.queryForObject("INSERT INTO products(id,category_id,slug,brand,title,description) VALUES (?,?,?,?,?,?) ON CONFLICT(slug) DO UPDATE SET category_id=excluded.category_id,brand=excluded.brand,title=excluded.title,description=excluded.description,revision=products.revision+CASE WHEN (products.category_id,products.brand,products.title,products.description) IS DISTINCT FROM (excluded.category_id,excluded.brand,excluded.title,excluded.description) THEN 1 ELSE 0 END,updated_at=CASE WHEN (products.category_id,products.brand,products.title,products.description) IS DISTINCT FROM (excluded.category_id,excluded.brand,excluded.title,excluded.description) THEN now() ELSE products.updated_at END WHERE products.status='draft' OR (products.category_id,products.brand,products.title,products.description) IS NOT DISTINCT FROM (excluded.category_id,excluded.brand,excluded.title,excluded.description) RETURNING id",UUID.class,UUID.randomUUID(),categoryId,slug,brand,title,description);
        return id;
    }

    UUID createSku(UUID productId, String code, Object attributes, String assetKey, String altText, String actor) {
        if (!assetKey.matches("[a-zA-Z0-9/_-]+\\.(svg|jpg|jpeg|png|webp)") || assetKey.startsWith("/") || assetKey.contains(".."))
            throw new IllegalArgumentException("assetKey must be a relative local image key");
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
        var product = jdbc.queryForMap("SELECT category_id,status,revision,details::text AS details FROM products WHERE id=? FOR UPDATE", productId);
        int revision = (Integer) product.get("revision");
        if (revision != expectedRevision) throw new StaleRevisionException();
        if (!"draft".equals(product.get("status"))) throw new IllegalArgumentException("Only draft products can be activated");
        if (jdbc.queryForObject("SELECT count(*) FROM skus WHERE product_id=? AND active", Integer.class, productId) == 0)
            throw new IllegalArgumentException("At least one active SKU is required");
        if (!"{}".equals(product.get("details"))) requirePhotographicSkus(productId);
        jdbc.update("UPDATE products SET status='active',revision=revision+1,updated_at=now() WHERE id=?", productId);
        audit("product", productId, "activate", actor, revision, revision + 1, Map.of());
    }

    private void requirePhotographicSkus(UUID productId) {
        if (jdbc.queryForObject("SELECT count(*) FROM skus WHERE product_id=? AND active AND asset_key !~ '^[a-zA-Z0-9_-]+(/[a-zA-Z0-9_-]+)*[.](jpg|jpeg|png|webp)$'",Integer.class,productId)>0)
            throw new IllegalArgumentException("Sourced products require photographic SKU asset keys");
    }

    private void audit(String type, UUID id, String action, String actor, Integer from, int to, Object details) {
        jdbc.update("INSERT INTO catalog_audit(entity_type,entity_id,action,actor,from_revision,to_revision,details) VALUES (?,?,?,?,?,?,?::jsonb)", type, id, action, actor, from, to, Json.write(details));
    }
}
