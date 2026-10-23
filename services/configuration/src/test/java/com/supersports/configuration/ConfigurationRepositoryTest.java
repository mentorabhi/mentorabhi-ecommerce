package com.supersports.configuration;

import java.sql.ResultSet;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.dao.DataAccessResourceFailureException;
import tools.jackson.databind.json.JsonMapper;
import static org.assertj.core.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class ConfigurationRepositoryTest {
    @Test void readsRevisionAndOrderedTypedRecordsThroughController() throws Exception {
        var jdbc = mock(JdbcTemplate.class);
        when(jdbc.queryForObject("SELECT revision FROM bootstrap_metadata WHERE service = 'configuration'", Long.class))
                .thenReturn(1L);
        when(jdbc.query(eq("SELECT id, label FROM configuration_category ORDER BY id"), any(RowMapper.class)))
                .thenAnswer(invocation -> {
                    RowMapper<?> mapper = invocation.getArgument(1);
                    var row = mock(ResultSet.class);
                    when(row.getString("id")).thenReturn("store-localization");
                    when(row.getString("label")).thenReturn("Store and localization");
                    return List.of(mapper.mapRow(row, 0));
                });
        when(jdbc.query(eq("SELECT key, category, value, value_type, activation_mode, revision FROM configuration_setting ORDER BY key"), any(RowMapper.class)))
                .thenAnswer(invocation -> {
                    RowMapper<?> mapper = invocation.getArgument(1);
                    var row = mock(ResultSet.class);
                    when(row.getString("key")).thenReturn("store.currency");
                    when(row.getString("category")).thenReturn("store-localization");
                    when(row.getString("value")).thenReturn("INR");
                    when(row.getString("value_type")).thenReturn("STRING");
                    when(row.getString("activation_mode")).thenReturn("MIGRATION_ONLY");
                    when(row.getLong("revision")).thenReturn(1L);
                    return List.of(mapper.mapRow(row, 0));
                });
        var snapshot = new ConfigurationController(new ConfigurationRepository(jdbc)).configuration();
        assertThat(snapshot.revision()).isEqualTo(1);
        assertThat(snapshot.categories()).containsExactly(new ConfigurationSnapshot.Category("store-localization", "Store and localization"));
        assertThat(snapshot.settings()).containsExactly(new ConfigurationSnapshot.Setting("store.currency", "store-localization", "INR",
                ConfigurationSnapshot.ValueType.STRING, ConfigurationSnapshot.ActivationMode.MIGRATION_ONLY, 1));
        var json = new JsonMapper().readTree(new JsonMapper().writeValueAsString(snapshot));
        assertThat(json.get("settings").get(0).get("value").asString()).isEqualTo("INR");
        assertThat(json.get("settings").get(0).get("valueType").asString()).isEqualTo("STRING");
        assertThat(json.get("settings").get(0).get("activationMode").asString()).isEqualTo("MIGRATION_ONLY");
        verify(jdbc).query(eq("SELECT id, label FROM configuration_category ORDER BY id"), any(RowMapper.class));
        verify(jdbc).query(eq("SELECT key, category, value, value_type, activation_mode, revision FROM configuration_setting ORDER BY key"), any(RowMapper.class));
    }

    @Test void databaseFailureIsPropagatedWithoutInventingDefaults() {
        var jdbc = mock(JdbcTemplate.class);
        when(jdbc.queryForObject(anyString(), eq(Long.class)))
                .thenThrow(new DataAccessResourceFailureException("unavailable"));
        assertThatThrownBy(() -> new ConfigurationRepository(jdbc).read())
                .isInstanceOf(DataAccessResourceFailureException.class);
        verify(jdbc).queryForObject(anyString(), eq(Long.class));
        verifyNoMoreInteractions(jdbc);
    }
}
