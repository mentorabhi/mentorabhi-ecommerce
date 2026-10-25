package com.supersports.catalog;

import java.util.List;
import org.junit.jupiter.api.Test;
import static org.assertj.core.api.Assertions.*;

class ProductDetailsTest {
    static ProductDetails details(String key,String alt,String source,String kind) {
        return new ProductDetails("Model A","bat",List.of("Sourced model"),null,null,null,null,List.of("One bat"),
                new ProductDetails.Provenance(source,"2026-10-25","Source attribution; educational local demonstration"),
                List.of(new ProductDetails.Photo(key,alt,kind)),"Prices and stock simulated; extra variants are demo data");
    }
    @Test void acceptsLocalPhotographWithExplicitSourceAndDemoCommerceProvenance() {
        assertThat(details("products/model-a.jpg","A bat","https://example.com/model-a","photograph").validated()).isNotNull();
    }
    @Test void rejectsRemoteTraversalIllustrationsAndUnsafeContent() {
        for(String key:List.of("../a.jpg","/a.jpg","https://example.com/a.jpg","a.svg","a.jpg?x=1","a//b.jpg"))
            assertThatThrownBy(()->details(key,"Bat","https://example.com/a","photograph").validated()).isInstanceOf(IllegalArgumentException.class);
        for(String url:List.of("javascript:alert(1)","file:///tmp/a","https://user:secret@example.com/a"))
            assertThatThrownBy(()->details("a.jpg","Bat",url,"photograph").validated()).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(()->details("a.jpg","<script>x</script>","https://example.com/a","photograph").validated()).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(()->details("a.jpg","Bat","https://example.com/a","illustration").validated()).isInstanceOf(IllegalArgumentException.class);
    }
}
