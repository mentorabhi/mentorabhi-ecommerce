CREATE TABLE inventory_return (
    return_id uuid PRIMARY KEY,
    order_id uuid NOT NULL,
    manifest_hash char(64) NOT NULL,
    state varchar(24) NOT NULL CHECK (state IN ('RECEIVED','INSPECTED')),
    revision bigint NOT NULL DEFAULT 0 CHECK (revision >= 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE inventory_return_unit (
    return_id uuid NOT NULL REFERENCES inventory_return(return_id),
    order_id uuid NOT NULL,
    sku_id uuid NOT NULL,
    unit_ordinal integer NOT NULL CHECK (unit_ordinal >= 0),
    condition varchar(16) NOT NULL DEFAULT 'PENDING' CHECK (condition IN ('PENDING','SELLABLE','DAMAGED','DISPUTED')),
    reason varchar(500),
    inspected_by varchar(160),
    inspected_at timestamptz,
    PRIMARY KEY(return_id,sku_id,unit_ordinal)
);
CREATE INDEX inventory_return_pending_idx ON inventory_return(state,created_at);

CREATE TABLE inventory_return_inspection_audit (
    operation_id uuid PRIMARY KEY,
    return_id uuid NOT NULL REFERENCES inventory_return(return_id),
    request_hash char(64) NOT NULL,
    previous_revision bigint NOT NULL,
    next_revision bigint NOT NULL,
    actor_subject varchar(160) NOT NULL,
    inspected_units integer NOT NULL CHECK (inspected_units > 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(return_id,next_revision)
);
