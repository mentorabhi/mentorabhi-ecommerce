package com.supersports.catalog;

import jakarta.servlet.Filter;
import java.util.*;
import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.context.annotation.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.mock.web.MockServletContext;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.oauth2.jwt.*;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.transaction.annotation.EnableTransactionManagement;
import org.springframework.web.context.support.AnnotationConfigWebApplicationContext;
import org.springframework.web.servlet.config.annotation.EnableWebMvc;
import static org.assertj.core.api.Assertions.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/** Runs only against an explicitly supplied PostgreSQL; owns and drops a fresh random schema. */
@EnabledIfEnvironmentVariable(named="CATALOG_TEST_JDBC_URL",matches=".+")
class CatalogBoundaryTest {
    private AnnotationConfigWebApplicationContext context;
    private MockMvc mvc;
    private JdbcTemplate jdbc;
    private DriverManagerDataSource base;
    private String schema;
    private CatalogRepository repository;
    private UUID cricket,football,category,otherCategory,source;

    @BeforeEach void start() {
        base=new DriverManagerDataSource(System.getenv("CATALOG_TEST_JDBC_URL"),System.getenv("CATALOG_TEST_DB_USER"),System.getenv("CATALOG_TEST_DB_PASSWORD"));
        schema="catalog_test_"+UUID.randomUUID().toString().replace("-","");
        new JdbcTemplate(base).execute("CREATE SCHEMA "+schema);
        String url=System.getenv("CATALOG_TEST_JDBC_URL");
        var ds=new DriverManagerDataSource(url+(url.contains("?")?"&":"?")+"currentSchema="+schema,System.getenv("CATALOG_TEST_DB_USER"),System.getenv("CATALOG_TEST_DB_PASSWORD"));
        Flyway.configure().dataSource(ds).defaultSchema(schema).schemas(schema).load().migrate();
        jdbc=new JdbcTemplate(ds);
        context=new AnnotationConfigWebApplicationContext();
        context.setServletContext(new MockServletContext());
        context.addBeanFactoryPostProcessor(factory -> {
            factory.registerSingleton("jdbc",jdbc);
            factory.registerSingleton("transactionManager",new DataSourceTransactionManager(ds));
        });
        context.register(ConfigurationForTest.class); context.refresh();
        mvc=MockMvcBuilders.webAppContextSetup(context).addFilters(context.getBean("springSecurityFilterChain",Filter.class)).build();
        repository=context.getBean(CatalogRepository.class);
        cricket=repository.createSport("cricket","Cricket","owner");
        football=repository.createSport("football","Football","owner");
        category=repository.createCategory(cricket,null,"bats","Bats",List.of(),"owner");
        otherCategory=repository.createCategory(football,null,"balls","Balls",List.of(),"owner");
        for(int i=0;i<55;i++) add(category,"bat-"+i,String.format("Bat %02d",i),"active",i==0?"bat":"");
        source=(UUID)jdbc.queryForMap("SELECT id FROM products WHERE slug='bat-0'").get("id");
    }
    @AfterEach void close() {
        if(context!=null) context.close();
        if(base!=null && schema!=null) new JdbcTemplate(base).execute("DROP SCHEMA "+schema+" CASCADE");
    }
    private UUID add(UUID cat,String slug,String title,String status,String equipment) {
        UUID id=repository.createProduct(cat,slug,"Brand",title,"Sourced description","owner");
        jdbc.update("UPDATE products SET status=?,details=?::jsonb WHERE id=?",status,equipment.isEmpty()?"{}":Json.write(Map.of("equipmentType",equipment)),id);
        return id;
    }
    @SuppressWarnings("unchecked") private Map<String,Object> body(String json) { return (Map<String,Object>)Json.read(json); }
    private String response(org.springframework.test.web.servlet.request.MockHttpServletRequestBuilder request) throws Exception {
        return mvc.perform(request).andExpect(status().isOk()).andReturn().getResponse().getContentAsString();
    }
    private Map<String,Object> update(int revision,String key,ProductDetails details) {
        return Map.of("expectedRevision",revision,"idempotencyKey",key,"brand","Brand","title","Updated Bat","description","Actual model facts","details",details);
    }
    @Test void pagesFilterLiterallyAndDetailWorksBeyondFirstPageWithSafeMigrationDefaults() throws Exception {
        var page=body(response(get("/api/v1/catalog/public/products")));
        assertThat((List<?>)page.get("items")).hasSize(24);
        assertThat(page).containsEntry("page",1).containsEntry("pageSize",24).containsEntry("total",55).containsEntry("hasNext",true);
        var last=body(response(get("/api/v1/catalog/public/products?page=3")));
        assertThat((List<?>)last.get("items")).hasSize(7); assertThat(last.get("hasNext")).isEqualTo(false);
        assertThat((List<?>)body(response(get("/api/v1/catalog/public/products?pageSize=48"))).get("items")).hasSize(48);
        assertThat((List<?>)body(response(get("/api/v1/catalog/public/products?page=10000"))).get("items")).isEmpty();
        for(String filter:List.of("q=%25","q=_","sport=football","category=missing"))
            assertThat(body(response(get("/api/v1/catalog/public/products?"+filter))).get("total")).isEqualTo(0);
        assertThat(body(response(get("/api/v1/catalog/public/products").param("q","Bat 54").param("category","bats").param("sport","cricket"))).get("total")).isEqualTo(1);
        assertThat(body(response(get("/api/v1/catalog/public/products/bat-54")))).containsEntry("slug","bat-54").containsEntry("details",Map.of());
        // The original list remains an array and its repository API/import calls still work.
        assertThat((List<?>)Json.read(response(get("/api/v1/catalog/products")))).hasSize(55);
        assertThat(repository.products(false)).hasSize(55);
    }
    @Test void searchSeparatesEquipmentFromAccessoriesAndFootballWithStableRelevanceAndPagination() throws Exception {
        add(category,"kit-with-bat","A cricket kit with bat","active","kit");
        add(category,"batting-pads","A Batting Pads","active","pads");
        add(category,"batting-gloves","A Batting Gloves","active","gloves");
        add(otherCategory,"football-jersey","A football jersey","active","jersey");
        add(otherCategory,"match-ball","Match football ball","active","ball");
        UUID model=add(category,"brand-model","Z Brand Pro","active","bat");
        jdbc.update("UPDATE products SET brand='SG',description='A cricket bat for practice' WHERE id=?",model);
        for(String q:List.of("bat","bats","a bat","show me a bat")) {
            var result=body(response(get("/api/v1/catalog/public/products").param("q",q).param("pageSize","48")));
            assertThat(result.get("total")).isEqualTo(56);
            @SuppressWarnings("unchecked") var items=(List<Map<String,Object>>)result.get("items");
            assertThat(items).noneMatch(item->List.of("kit-with-bat","batting-pads","batting-gloves","football-jersey","match-ball").contains(item.get("slug")));
        }
        var finalPage=body(response(get("/api/v1/catalog/public/products").param("q","bats").param("page","3")));
        assertThat((List<?>)finalPage.get("items")).hasSize(8);
        for(String q:List.of("SG cricket bat","bat SG cricket"))
            assertThat(body(response(get("/api/v1/catalog/public/products").param("q",q))).get("total")).isEqualTo(1);
        assertThat(body(response(get("/api/v1/catalog/public/products").param("q","balls"))).get("total")).isEqualTo(1);
        assertThat(body(response(get("/api/v1/catalog/public/products").param("q","pads"))).get("total")).isEqualTo(1);
        assertThat(body(response(get("/api/v1/catalog/public/products").param("q","football"))).get("total")).isEqualTo(2);
        assertThat(body(response(get("/api/v1/catalog/public/products").param("q","bat").param("sport","football"))).get("total")).isEqualTo(0);
        String query=response(get("/api/v1/catalog/public/products").param("q","practice"));
        assertThat(query).isEqualTo(response(get("/api/v1/catalog/public/products").param("q","practice")));
        UUID exact=add(category,"practice-title","Practice","active","bat");
        @SuppressWarnings("unchecked") var ranked=(List<Map<String,Object>>)body(response(get("/api/v1/catalog/public/products").param("q","practice"))).get("items");
        assertThat(ranked.getFirst().get("id")).isEqualTo(exact.toString());
        jdbc.update("UPDATE products SET status='retired' WHERE id=?",exact);
        assertThat(body(response(get("/api/v1/catalog/public/products").param("q","practice"))).get("total")).isEqualTo(1);
        for(String q:List.of("%","_","!","show me a","missing-model"))
            assertThat(body(response(get("/api/v1/catalog/public/products").param("q",q))).get("total")).isEqualTo(0);
    }
    @Test void compoundAccessoryQueriesFindAccessoriesWithoutLeakingThemIntoBatSearch() throws Exception {
        add(category,"sg-grip","SG Cricket Bat Grip","active","bat-grip");
        add(category,"dsc-oil","DSC Linseed Cricket Bat Oil","active","bat-oil");
        add(category,"practice-tee","Cricket Batting Tee","active","batting-tee");
        for(String q:List.of("bat grip","bat grips","bat oil","linseed oil","batting tee"))
            assertThat(body(response(get("/api/v1/catalog/public/products").param("q",q))).get("total")).isEqualTo(1);
        assertThat(body(response(get("/api/v1/catalog/public/products").param("q","bat"))).get("total")).isEqualTo(55);
        assertThat(body(response(get("/api/v1/catalog/public/products").param("q","missingbrand bat grip"))).get("total")).isEqualTo(0);
    }
    @Test void similarRanksDeterministicallyAndExcludesCurrentRetiredAndInactiveParents() throws Exception {
        UUID same=add(category,"same-equipment","Z same equipment","active","bat");
        UUID cross=add(otherCategory,"cross-equipment","A cross sport","active","bat");
        add(category,"retired","A retired","retired","bat");
        add(category,"draft","A draft","draft","bat");
        UUID hiddenSport=repository.createSport("hidden","Hidden","owner");
        UUID hiddenCategory=repository.createCategory(hiddenSport,null,"hidden","Hidden",List.of(),"owner");
        add(hiddenCategory,"hidden","A hidden sport","active","bat");
        jdbc.update("UPDATE sports SET active=false WHERE id=?",hiddenSport);
        String first=response(get("/api/v1/catalog/public/products/bat-0/similar?limit=12"));
        assertThat(response(get("/api/v1/catalog/public/products/bat-0/similar?limit=12"))).isEqualTo(first);
        @SuppressWarnings("unchecked") var items=(List<Map<String,Object>>)Json.read(first);
        assertThat(items).hasSize(12); assertThat(items.getFirst().get("id")).isEqualTo(same.toString());
        assertThat(items).noneMatch(p->List.of(source.toString(),cross.toString()).contains(p.get("id")) || List.of("draft","retired","hidden").contains(p.get("slug")));
        mvc.perform(get("/api/v1/catalog/public/products/retired")).andExpect(status().isNotFound());
        mvc.perform(get("/api/v1/catalog/public/products/retired/similar")).andExpect(status().isNotFound());
        jdbc.update("UPDATE categories SET active=false WHERE id=?",category);
        mvc.perform(get("/api/v1/catalog/public/products/bat-0")).andExpect(status().isNotFound());
    }
    @Test void savedSkuLookupFindsModelsBeyondBrowsePageAndExcludesRetired() throws Exception {
        UUID product=(UUID)jdbc.queryForMap("SELECT id FROM products WHERE slug='bat-54'").get("id");
        UUID sku=UUID.randomUUID();
        jdbc.update("INSERT INTO skus(id,product_id,code,asset_key,alt_text) VALUES (?,?,?,'products/bat.jpg','Bat')",sku,product,"SAVED-SKU");
        var items=(List<?>)Json.read(response(get("/api/v1/catalog/public/products/by-skus").param("skuIds",sku.toString())));
        assertThat(items).hasSize(1);
        assertThat(((Map<?,?>)items.getFirst()).get("slug")).isEqualTo("bat-54");
        assertThat((List<?>)Json.read(response(get("/api/v1/catalog/public/products/by-skus").param("skuIds",UUID.randomUUID().toString())))).isEmpty();
        mvc.perform(get("/api/v1/catalog/public/products/by-skus").param("skuIds",sku+","+sku)).andExpect(status().isBadRequest());
        jdbc.update("UPDATE products SET status='retired' WHERE id=?",product);
        assertThat((List<?>)Json.read(response(get("/api/v1/catalog/public/products/by-skus").param("skuIds",sku.toString())))).isEmpty();
    }
    @Test void revisionedUpdateRetirementReplayAndHistoricalSkuSurviveRealHttpAndTransactions() throws Exception {
        UUID sku=UUID.randomUUID();
        jdbc.update("INSERT INTO skus(id,product_id,code,asset_key,alt_text) VALUES (?,?,?,'products/bat.jpg','Bat')",sku,source,"HISTORIC");
        ProductDetails details=ProductDetailsTest.details("products/bat.jpg","Bat","https://example.com/bat","photograph");
        String payload=Json.write(update(1,"update-key-1",details));
        String result=response(put("/api/v1/catalog/products/"+source).header("Authorization","Bearer owner").contentType("application/json").content(payload));
        assertThat(body(result)).containsEntry("revision",2);
        assertThat(body(response(put("/api/v1/catalog/products/"+source).header("Authorization","Bearer owner").contentType("application/json").content(payload)))).isEqualTo(body(result));
        assertThat(body(response(get("/api/v1/catalog/public/products/bat-0"))).get("details")).isEqualTo(Json.read(Json.write(details)));
        mvc.perform(put("/api/v1/catalog/products/"+source).header("Authorization","Bearer owner").contentType("application/json").content(Json.write(update(1,"stale-key",details)))).andExpect(status().isConflict());
        mvc.perform(put("/api/v1/catalog/products/"+source).header("Authorization","Bearer other-owner").contentType("application/json").content(payload)).andExpect(status().isConflict());
        mvc.perform(put("/api/v1/catalog/products/"+source).header("Authorization","Bearer owner").contentType("application/json").content(Json.write(update(2,"update-key-1",details)))).andExpect(status().isConflict());
        String retire=Json.write(Map.of("expectedRevision",2,"idempotencyKey","retire-key","reason","Replaced fictional listing"));
        for(int i=0;i<2;i++) assertThat(body(response(post("/api/v1/catalog/products/"+source+"/retire").header("Authorization","Bearer owner").contentType("application/json").content(retire)))).containsEntry("status","retired").containsEntry("revision",3);
        mvc.perform(get("/api/v1/catalog/public/products/bat-0")).andExpect(status().isNotFound());
        assertThat(repository.checkoutSku(sku)).containsEntry("productId",source).containsEntry("active",false).containsEntry("title","Updated Bat");
        assertThat(repository.publicSku(sku)).containsEntry("id",sku).containsEntry("active",false);
        assertThat(jdbc.queryForObject("SELECT code FROM skus WHERE id=?",String.class,sku)).isEqualTo("HISTORIC");
        assertThat(jdbc.queryForObject("SELECT count(*) FROM catalog_audit WHERE entity_id=?",Integer.class,source)).isEqualTo(2);
        assertThat(repository.createProduct(category,"bat-0","Brand","Updated Bat","Actual model facts","owner")).isEqualTo(source);
        assertThatThrownBy(()->repository.createProduct(category,"bat-0","Other","Changed","Oops","owner")).isInstanceOf(org.springframework.dao.EmptyResultDataAccessException.class);
    }
    @Test void ownerAuthenticationAndInvalidDetailsCannotWriteOrIncrementRevision() throws Exception {
        var details=ProductDetailsTest.details("../bat.jpg","Bat","https://example.com/bat","photograph");
        var request=Json.write(update(1,"invalid-key",details));
        mvc.perform(put("/api/v1/catalog/products/"+source).contentType("application/json").content(request)).andExpect(status().isUnauthorized());
        mvc.perform(put("/api/v1/catalog/products/"+source).header("Authorization","Bearer customer").contentType("application/json").content(request)).andExpect(status().isForbidden());
        mvc.perform(put("/api/v1/catalog/products/"+source).header("Authorization","Bearer owner").contentType("application/json").content(request)).andExpect(status().isUnprocessableEntity());
        mvc.perform(post("/api/v1/catalog/products/"+source+"/retire").header("Authorization","Bearer customer").contentType("application/json").content("{}")).andExpect(status().isForbidden());
        assertThat(jdbc.queryForObject("SELECT revision FROM products WHERE id=?",Integer.class,source)).isEqualTo(1);
        assertThat(jdbc.queryForObject("SELECT count(*) FROM catalog_mutations",Integer.class)).isZero();
    }
    @Test void concurrentRevisionWritersHaveOneWinnerAndReplayDoesNotDuplicateAudit() throws Exception {
        try(var workers=java.util.concurrent.Executors.newVirtualThreadPerTaskExecutor()) {
            var ready=new java.util.concurrent.CountDownLatch(2);
            var go=new java.util.concurrent.CountDownLatch(1);
            var futures=new ArrayList<java.util.concurrent.Future<Integer>>();
            for(int i=0;i<2;i++) {
                String key="concurrent-key-"+i;
                futures.add(workers.submit(()->{
                    ready.countDown(); go.await();
                    return mvc.perform(post("/api/v1/catalog/products/"+source+"/retire").header("Authorization","Bearer owner").contentType("application/json")
                            .content(Json.write(Map.of("expectedRevision",1,"idempotencyKey",key,"reason","Replace listing")))).andReturn().getResponse().getStatus();
                }));
            }
            assertThat(ready.await(5,java.util.concurrent.TimeUnit.SECONDS)).isTrue(); go.countDown();
            var statuses=new ArrayList<Integer>();
            for(var future:futures) statuses.add(future.get(10,java.util.concurrent.TimeUnit.SECONDS));
            assertThat(statuses).containsExactlyInAnyOrder(200,409);
            assertThat(jdbc.queryForObject("SELECT count(*) FROM catalog_audit WHERE entity_id=?",Integer.class,source)).isEqualTo(1);
            assertThat(jdbc.queryForObject("SELECT count(*) FROM catalog_mutations",Integer.class)).isEqualTo(1);
        }
    }
    @Test void sourcedActivationRejectsLegacyIllustratedSkuWhileLegacyImportsRemainUsable() {
        UUID draft=repository.createProduct(category,"new-draft","Brand","New draft","Model facts","owner");
        UUID sku=repository.createSku(draft,"DRAFT-SKU",Map.of(),"products/legacy.svg","Legacy illustration","owner");
        var details=ProductDetailsTest.details("products/bat.jpg","Bat","https://example.com/bat","photograph");
        repository.updateProduct(draft,1,"draft-update","owner","Brand","New draft","Model facts",details);
        assertThatThrownBy(()->repository.activate(draft,2,"owner")).isInstanceOf(IllegalArgumentException.class).hasMessageContaining("photographic SKU");
        assertThat(jdbc.queryForObject("SELECT status FROM products WHERE id=?",String.class,draft)).isEqualTo("draft");
        assertThat(repository.createSku(draft,"DRAFT-SKU",Map.of(),"products/bat.jpg","Photographic bat","owner")).isEqualTo(sku);
        repository.activate(draft,2,"owner");
        assertThat(repository.checkoutSku(sku)).containsEntry("active",true);
    }
    @Configuration(proxyBeanMethods=false) @EnableWebSecurity @EnableWebMvc @EnableTransactionManagement
    @Import({SecurityConfiguration.class,CatalogRepository.class,CatalogBrowseController.class,CatalogMutationController.class})
    static class ConfigurationForTest {
        @Bean CatalogController legacy(CatalogRepository repository) { return new CatalogController(repository,"http://localhost:1"); }
        @Bean JwtDecoder decoder() {
            return token -> {
                if(!Set.of("owner","other-owner","customer").contains(token)) throw new BadJwtException("Invalid token");
                return Jwt.withTokenValue(token).header("alg","RS256").subject(token).audience(List.of(token.equals("customer")?"supersports-customer-api":"supersports-api")).build();
            };
        }
    }
}
