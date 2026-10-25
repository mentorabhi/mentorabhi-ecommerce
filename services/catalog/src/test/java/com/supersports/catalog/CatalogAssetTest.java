package com.supersports.catalog;
import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;

class CatalogAssetTest {
    @Test void localPhotographsPassAssetValidationButRemoteAndTraversalKeysFail() {
        var jdbc = mock(JdbcTemplate.class);
        var repository = new CatalogRepository(jdbc);
        var id = UUID.randomUUID();
        when(jdbc.queryForObject(anyString(),eq(Integer.class),eq(id))).thenReturn(0);
        assertThatThrownBy(() -> repository.createSku(id,"DEMO",Map.of(),"products/synthetic/cricket-bat.jpg","Demo bat","tester"))
            .isInstanceOf(IllegalArgumentException.class).hasMessage("SKUs can only be added to draft products");
        for (String key : new String[]{"../bat.jpg","/bat.jpg","https://example.com/bat.jpg","products/bat.exe"})
            assertThatThrownBy(() -> repository.createSku(id,"DEMO",Map.of(),key,"Demo bat","tester"))
                .isInstanceOf(IllegalArgumentException.class).hasMessageContaining("relative local");
    }
}
