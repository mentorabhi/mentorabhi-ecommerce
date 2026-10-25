-- Legacy listings remain readable; unknown facts and provenance are not invented.
ALTER TABLE products ADD COLUMN details jsonb NOT NULL DEFAULT '{}'::jsonb
    CHECK (jsonb_typeof(details) = 'object');
CREATE INDEX products_browse_idx ON products(status, title, id);
CREATE TABLE catalog_mutations (
    idempotency_key varchar(120) PRIMARY KEY,
    actor varchar(160) NOT NULL,
    request jsonb NOT NULL,
    response jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
