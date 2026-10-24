CREATE TABLE sports (
    id uuid PRIMARY KEY,
    slug varchar(64) NOT NULL UNIQUE,
    name varchar(120) NOT NULL,
    active boolean NOT NULL DEFAULT true,
    revision integer NOT NULL DEFAULT 1 CHECK (revision > 0)
);

CREATE TABLE categories (
    id uuid PRIMARY KEY,
    sport_id uuid NOT NULL REFERENCES sports(id),
    parent_id uuid REFERENCES categories(id),
    slug varchar(64) NOT NULL,
    name varchar(120) NOT NULL,
    attributes jsonb NOT NULL DEFAULT '[]'::jsonb,
    active boolean NOT NULL DEFAULT true,
    revision integer NOT NULL DEFAULT 1 CHECK (revision > 0),
    UNIQUE (sport_id, slug),
    CHECK (parent_id IS NULL OR parent_id <> id)
);

CREATE TABLE products (
    id uuid PRIMARY KEY,
    category_id uuid NOT NULL REFERENCES categories(id),
    slug varchar(100) NOT NULL UNIQUE,
    brand varchar(120) NOT NULL,
    title varchar(200) NOT NULL,
    description text NOT NULL,
    status varchar(16) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','active','retired')),
    revision integer NOT NULL DEFAULT 1 CHECK (revision > 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE skus (
    id uuid PRIMARY KEY,
    product_id uuid NOT NULL REFERENCES products(id),
    code varchar(100) NOT NULL UNIQUE,
    attributes jsonb NOT NULL DEFAULT '{}'::jsonb,
    asset_key varchar(200) NOT NULL,
    alt_text varchar(240) NOT NULL,
    active boolean NOT NULL DEFAULT true,
    revision integer NOT NULL DEFAULT 1 CHECK (revision > 0)
);

CREATE TABLE catalog_audit (
    id bigserial PRIMARY KEY,
    entity_type varchar(32) NOT NULL,
    entity_id uuid NOT NULL,
    action varchar(32) NOT NULL,
    actor varchar(160) NOT NULL,
    from_revision integer,
    to_revision integer NOT NULL,
    details jsonb NOT NULL DEFAULT '{}'::jsonb,
    occurred_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX catalog_audit_entity_idx ON catalog_audit(entity_type, entity_id, occurred_at DESC);
