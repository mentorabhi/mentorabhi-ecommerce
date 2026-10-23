CREATE TABLE bootstrap_metadata (
    service varchar(64) PRIMARY KEY CHECK (service = 'configuration'),
    schema_version integer NOT NULL CHECK (schema_version > 0),
    revision bigint NOT NULL CHECK (revision > 0)
);
INSERT INTO bootstrap_metadata (service, schema_version, revision) VALUES ('configuration', 1, 1);

CREATE TABLE configuration_category (
    id varchar(64) PRIMARY KEY,
    label varchar(128) NOT NULL
);
CREATE TABLE configuration_setting (
    key varchar(128) PRIMARY KEY,
    category varchar(64) NOT NULL REFERENCES configuration_category(id),
    value text NOT NULL,
    value_type varchar(32) NOT NULL CHECK (value_type IN ('STRING', 'STRING_LIST', 'BOOLEAN')),
    activation_mode varchar(32) NOT NULL CHECK (activation_mode = 'MIGRATION_ONLY'),
    revision bigint NOT NULL CHECK (revision > 0)
);
INSERT INTO configuration_category (id, label) VALUES
    ('store-localization', 'Store and localization'),
    ('commerce-simulations', 'Commerce simulations'),
    ('storage', 'Storage'),
    ('search-cache', 'Search and cache'),
    ('messaging-workflows', 'Messaging and workflows'),
    ('identity-access', 'Identity and access'),
    ('observability', 'Observability'),
    ('nova-models', 'Nova models');

-- Registry metadata only: no dynamic adapter selection or activation is implemented.
-- STRING_LIST is a JSON array encoded in the string value.
INSERT INTO configuration_setting (key, category, value, value_type, activation_mode, revision) VALUES
    ('store.currency', 'store-localization', 'INR', 'STRING', 'MIGRATION_ONLY', 1),
    ('store.country', 'store-localization', 'IN', 'STRING', 'MIGRATION_ONLY', 1),
    ('store.language', 'store-localization', 'en', 'STRING', 'MIGRATION_ONLY', 1),
    ('store.supported-currencies', 'store-localization', '["INR","USD"]', 'STRING_LIST', 'MIGRATION_ONLY', 1),
    ('simulation.payment', 'commerce-simulations', 'simulated', 'STRING', 'MIGRATION_ONLY', 1),
    ('simulation.shipping', 'commerce-simulations', 'simulated', 'STRING', 'MIGRATION_ONLY', 1),
    ('simulation.tax', 'commerce-simulations', 'simulated', 'STRING', 'MIGRATION_ONLY', 1),
    ('storage.provider', 'storage', 'local', 'STRING', 'MIGRATION_ONLY', 1),
    ('search.provider', 'search-cache', 'unconfigured', 'STRING', 'MIGRATION_ONLY', 1),
    ('cache.provider', 'search-cache', 'unconfigured', 'STRING', 'MIGRATION_ONLY', 1),
    ('messaging.provider', 'messaging-workflows', 'unconfigured', 'STRING', 'MIGRATION_ONLY', 1),
    ('identity.provider', 'identity-access', 'local-keycloak', 'STRING', 'MIGRATION_ONLY', 1),
    ('observability.health-enabled', 'observability', 'true', 'BOOLEAN', 'MIGRATION_ONLY', 1),
    ('nova.endpoint-kind', 'nova-models', 'local-only', 'STRING', 'MIGRATION_ONLY', 1);
