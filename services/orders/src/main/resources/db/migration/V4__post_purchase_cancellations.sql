CREATE TABLE post_purchase_operation (
    operation_id uuid PRIMARY KEY,
    order_id uuid NOT NULL REFERENCES customer_order(id),
    customer_subject varchar(160) NOT NULL,
    idempotency_key varchar(120) NOT NULL,
    payload_hash char(64) NOT NULL,
    operation_type varchar(24) NOT NULL CHECK (operation_type IN ('CANCEL')),
    status varchar(24) NOT NULL CHECK (status IN ('PENDING','RUNNING','COMPLETED','REJECTED','MANUAL_REVIEW')),
    current_step varchar(40) NOT NULL,
    fence bigint NOT NULL,
    expected_shipment_revision bigint NOT NULL CHECK (expected_shipment_revision >= 0),
    attempt integer NOT NULL DEFAULT 0,
    lease_owner varchar(160),
    lease_until timestamptz,
    next_attempt_at timestamptz NOT NULL DEFAULT now(),
    last_error_code varchar(80),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(customer_subject,idempotency_key),
    UNIQUE(order_id,operation_type)
);
CREATE INDEX post_purchase_claim_idx ON post_purchase_operation(next_attempt_at) WHERE status IN ('PENDING','RUNNING');

CREATE TABLE post_purchase_operation_step (
    operation_id uuid NOT NULL REFERENCES post_purchase_operation(operation_id),
    step varchar(40) NOT NULL,
    operation_key varchar(200) NOT NULL UNIQUE,
    state varchar(20) NOT NULL CHECK (state IN ('SUCCEEDED','SKIPPED')),
    result jsonb NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY(operation_id,step)
);
