package com.supersports.configuration;

import java.util.List;

public record ConfigurationSnapshot(long revision, List<Category> categories, List<Setting> settings) {
    public record Category(String id, String label) {}
    public record Setting(String key, String category, String value, ValueType valueType,
                          ActivationMode activationMode, long revision) {}
    public enum ValueType { STRING, STRING_LIST, BOOLEAN }
    public enum ActivationMode { MIGRATION_ONLY, OPERATOR_EDITABLE }
}
