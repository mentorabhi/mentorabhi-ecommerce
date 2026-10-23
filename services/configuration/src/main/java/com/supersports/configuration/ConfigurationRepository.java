package com.supersports.configuration;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.transaction.annotation.Transactional;

@Repository
class ConfigurationRepository {
    private final JdbcTemplate jdbc;

    ConfigurationRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @Transactional(readOnly = true, isolation = Isolation.REPEATABLE_READ)
    public ConfigurationSnapshot read() {
        long revision = jdbc.queryForObject("SELECT revision FROM bootstrap_metadata WHERE service = 'configuration'", Long.class);
        var categories = jdbc.query("SELECT id, label FROM configuration_category ORDER BY id",
                (row, index) -> new ConfigurationSnapshot.Category(row.getString("id"), row.getString("label")));
        var settings = jdbc.query("SELECT key, category, value, value_type, activation_mode, revision FROM configuration_setting ORDER BY key",
                (row, index) -> new ConfigurationSnapshot.Setting(row.getString("key"), row.getString("category"),
                        row.getString("value"), ConfigurationSnapshot.ValueType.valueOf(row.getString("value_type")),
                        ConfigurationSnapshot.ActivationMode.valueOf(row.getString("activation_mode")), row.getLong("revision")));
        return new ConfigurationSnapshot(revision, categories, settings);
    }
}
