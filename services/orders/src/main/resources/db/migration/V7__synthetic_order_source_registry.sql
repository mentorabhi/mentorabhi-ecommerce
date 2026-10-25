CREATE TABLE synthetic_order_source (
    source_ref varchar(120) PRIMARY KEY,
    order_id uuid NOT NULL UNIQUE REFERENCES customer_order(id),
    payload_hash char(64) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
