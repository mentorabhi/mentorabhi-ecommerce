CREATE TABLE bootstrap_metadata (
    service varchar(64) PRIMARY KEY CHECK (service = 'catalog'),
    schema_version integer NOT NULL CHECK (schema_version > 0)
);
INSERT INTO bootstrap_metadata (service, schema_version) VALUES ('catalog', 1);
