package com.supersports.catalog;

import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.dao.DataAccessResourceFailureException;
import tools.jackson.databind.json.JsonMapper;
import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;

class CatalogControllerTest {
    @Test void reportsMigratedSchemaAndExactPublicShape() throws Exception {
        var jdbc = mock(JdbcTemplate.class);
        when(jdbc.queryForObject("SELECT max(version::integer) FROM flyway_schema_history WHERE success", Integer.class))
                .thenReturn(2);
        var response = new CatalogController(new CatalogRepository(jdbc), "http://localhost").status();
        assertThat(new JsonMapper().writeValueAsString(response))
                .isEqualTo("{\"service\":\"catalog\",\"status\":\"ready\",\"schemaVersion\":2}");
    }

    @Test void unavailableDatabaseDoesNotProduceAReadyResponse() {
        var jdbc = mock(JdbcTemplate.class);
        when(jdbc.queryForObject(anyString(), eq(Integer.class)))
                .thenThrow(new DataAccessResourceFailureException("unavailable"));
        assertThatThrownBy(() -> new CatalogController(new CatalogRepository(jdbc), "http://localhost").status())
                .isInstanceOf(DataAccessResourceFailureException.class);
    }
}
