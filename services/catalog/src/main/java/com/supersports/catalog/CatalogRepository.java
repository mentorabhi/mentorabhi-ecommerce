package com.supersports.catalog;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
class CatalogRepository {
    private final JdbcTemplate jdbc;

    CatalogRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    int schemaVersion() {
        return jdbc.queryForObject("SELECT schema_version FROM bootstrap_metadata WHERE service = 'catalog'", Integer.class);
    }
}
