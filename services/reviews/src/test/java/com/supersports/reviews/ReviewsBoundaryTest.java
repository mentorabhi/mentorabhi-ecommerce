package com.supersports.reviews;

import java.util.*;
import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.context.annotation.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.transaction.annotation.EnableTransactionManagement;
import static org.assertj.core.api.Assertions.*;

@EnabledIfEnvironmentVariable(named="REVIEWS_TEST_JDBC_URL",matches=".+")
class ReviewsBoundaryTest {
    DriverManagerDataSource base;
    JdbcTemplate jdbc;
    AnnotationConfigApplicationContext context;
    ReviewsRepository repository;
    String schema;
    UUID legacyId=UUID.randomUUID(), product=UUID.randomUUID();
    Map<String,Object> legacy;

    @BeforeEach void start() {
        String url=System.getenv("REVIEWS_TEST_JDBC_URL");
        String user=System.getenv("REVIEWS_TEST_DB_USER"),password=System.getenv("REVIEWS_TEST_DB_PASSWORD");
        base=new DriverManagerDataSource(url,user,password);
        schema="reviews_test_"+UUID.randomUUID().toString().replace("-","");
        new JdbcTemplate(base).execute("CREATE SCHEMA "+schema);
        var ds=new DriverManagerDataSource(url+(url.contains("?")?"&":"?")+"currentSchema="+schema,user,password);
        Flyway.configure().dataSource(ds).defaultSchema(schema).schemas(schema).target("1").load().migrate();
        jdbc=new JdbcTemplate(ds);
        jdbc.update("INSERT INTO product_review(id,customer_subject,order_id,product_id,sku_id,rating,title,body,state,revision) VALUES (?,'legacy-owner',?,?,?,5,'Legacy title','Legacy body','PUBLISHED',3)",legacyId,UUID.randomUUID(),product,UUID.randomUUID());
        legacy=jdbc.queryForMap("SELECT * FROM product_review WHERE id=?",legacyId);
        Flyway.configure().dataSource(ds).defaultSchema(schema).schemas(schema).load().migrate();
        context=new AnnotationConfigApplicationContext();
        context.addBeanFactoryPostProcessor(factory->{factory.registerSingleton("jdbc",jdbc);factory.registerSingleton("transactionManager",new DataSourceTransactionManager(ds));});
        context.register(Config.class);context.refresh();
        repository=context.getBean(ReviewsRepository.class);
    }
    @AfterEach void close() {
        if(context!=null)context.close();
        if(base!=null&&schema!=null)new JdbcTemplate(base).execute("DROP SCHEMA "+schema+" CASCADE");
    }
    @Test void migrationPreservesLegacyOwnershipAndDatabaseRejectsInvalidOrigins() {
        var migrated=jdbc.queryForMap("SELECT * FROM product_review WHERE id=?",legacyId);
        assertThat(migrated).containsAllEntriesOf(legacy).containsEntry("origin","CUSTOMER");
        assertThatThrownBy(()->jdbc.update("INSERT INTO product_review(id,product_id,rating,title,body) VALUES (?,?,5,'No owner','Invalid')",UUID.randomUUID(),product)).isInstanceOf(org.springframework.dao.DataIntegrityViolationException.class);
        assertThatThrownBy(()->jdbc.update("INSERT INTO product_review(id,product_id,rating,title,body,origin) VALUES (?,?,2,'Demo','Invalid','DEMO')",UUID.randomUUID(),product)).isInstanceOf(org.springframework.dao.DataIntegrityViolationException.class);
        var publicReview=repository.published(product).getFirst();
        assertThat(publicReview).containsEntry("origin","CUSTOMER").containsEntry("verifiedDelivered",true);
        assertThat(publicReview).doesNotContainKeys("customer_subject","customerSubject","orderId","skuId");
    }
    @Test void summaryModerationAndReplayNeverRepublishHiddenDemo() {
        UUID operation=UUID.randomUUID();
        assertThat(repository.seed(operation,"operator",List.of(product),3)).containsEntry("createdCount",3).containsEntry("replayed",false);
        var summary=repository.summaries(List.of(product)).getFirst();
        assertThat(summary.get("count")).isEqualTo(4L);
        assertThat(summary.get("mean")).isEqualTo(new java.math.BigDecimal("4.25"));
        UUID demo=DemoReviews.id(product,0);
        repository.moderate(demo,"HIDDEN","operator","Hide demonstration",UUID.randomUUID());
        assertThat(repository.seed(operation,"operator",List.of(product),3)).containsEntry("replayed",true);
        assertThat(repository.seed(UUID.randomUUID(),"operator",List.of(product),4)).containsEntry("createdCount",1);
        assertThat(jdbc.queryForObject("SELECT state FROM product_review WHERE id=?",String.class,demo)).isEqualTo("HIDDEN");
        assertThat(repository.published(product)).hasSize(4);
        assertThat(repository.moderationRows("HIDDEN",product)).hasSize(1).first().extracting(row->row.get("reviewId")).isEqualTo(demo);
        assertThat(repository.summaries(List.of(product)).getFirst().get("count")).isEqualTo(4L);
        assertThatThrownBy(()->repository.seed(operation,"other-operator",List.of(product),3)).isInstanceOf(IllegalStateException.class);
    }
    @Test void concurrentIdenticalSeedHasOneReceiptAndExactlyThreeDemoRows() throws Exception {
        UUID target=UUID.randomUUID(),operation=UUID.randomUUID();
        try(var workers=java.util.concurrent.Executors.newVirtualThreadPerTaskExecutor()) {
            var ready=new java.util.concurrent.CountDownLatch(2);var go=new java.util.concurrent.CountDownLatch(1);
            var tasks=new ArrayList<java.util.concurrent.Future<Map<String,Object>>>();
            for(int i=0;i<2;i++)tasks.add(workers.submit(()->{ready.countDown();go.await();return repository.seed(operation,"operator",List.of(target),3);}));
            assertThat(ready.await(5,java.util.concurrent.TimeUnit.SECONDS)).isTrue();go.countDown();
            var replayed=new ArrayList<Boolean>();
            for(var task:tasks)replayed.add((Boolean)task.get(15,java.util.concurrent.TimeUnit.SECONDS).get("replayed"));
            assertThat(replayed).containsExactlyInAnyOrder(false,true);
        }
        assertThat(repository.published(target)).hasSize(3);
        assertThat(jdbc.queryForObject("SELECT count(*) FROM review_demo_seed_operation WHERE operation_id=?",Integer.class,operation)).isEqualTo(1);
    }
    @Test void conflictingLaterSlotRollsBackEarlierProductAndReceipt() {
        UUID first=UUID.fromString("00000000-0000-0000-0000-000000000001"),second=UUID.fromString("00000000-0000-0000-0000-000000000002");
        UUID operation=UUID.randomUUID();
        jdbc.update("INSERT INTO product_review(id,product_id,rating,title,body,origin,state) VALUES (?,?,4,'Conflicting title','Conflicting body','DEMO','PUBLISHED')",DemoReviews.id(second,0),second);
        assertThatThrownBy(()->repository.seed(operation,"operator",List.of(first,second),3)).isInstanceOf(IllegalStateException.class);
        assertThat(repository.published(first)).isEmpty();
        assertThat(jdbc.queryForObject("SELECT count(*) FROM review_demo_seed_operation WHERE operation_id=?",Integer.class,operation)).isZero();
    }
    @Configuration(proxyBeanMethods=false) @EnableTransactionManagement @Import(ReviewsRepository.class)
    static class Config {}
}
