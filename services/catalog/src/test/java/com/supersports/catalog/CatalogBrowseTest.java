package com.supersports.catalog;

import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

class CatalogBrowseTest {
    @Test void publicBoundsAndDefaultsGoThroughHttpBinding() throws Exception {
        var repository = mock(CatalogRepository.class);
        var mvc = MockMvcBuilders.standaloneSetup(new CatalogBrowseController(repository)).build();
        mvc.perform(get("/api/v1/catalog/public/products")).andExpect(status().isOk());
        verify(repository).browse(1,24,null,null,null);
        for (String query : new String[]{"page=0", "page=10001", "pageSize=0", "pageSize=49", "q="+"a".repeat(101), "sport="+"a".repeat(65), "category="+"a".repeat(65)})
            mvc.perform(get("/api/v1/catalog/public/products?"+query)).andExpect(status().isBadRequest());
        mvc.perform(get("/api/v1/catalog/public/products/bat/similar?limit=0")).andExpect(status().isBadRequest());
        mvc.perform(get("/api/v1/catalog/public/products/bat/similar?limit=13")).andExpect(status().isBadRequest());
    }
}
