CREATE TABLE return_request (
    return_id uuid PRIMARY KEY,
    order_id uuid NOT NULL REFERENCES customer_order(id),
    customer_subject varchar(160) NOT NULL,
    idempotency_key varchar(120) NOT NULL,
    payload_hash char(64) NOT NULL,
    status varchar(24) NOT NULL CHECK (status IN ('PENDING','RUNNING','COMPLETED','MANUAL_REVIEW')),
    current_step varchar(32) NOT NULL,
    amount_minor bigint NOT NULL CHECK (amount_minor >= 0),
    currency char(3) NOT NULL,
    policy_revision bigint NOT NULL CHECK (policy_revision > 0),
    window_days integer NOT NULL CHECK (window_days BETWEEN 1 AND 90),
    delivered_at timestamptz NOT NULL,
    fence bigint NOT NULL DEFAULT 0,
    attempt integer NOT NULL DEFAULT 0,
    lease_owner varchar(160),
    lease_until timestamptz,
    next_attempt_at timestamptz NOT NULL DEFAULT now(),
    last_error_code varchar(80),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(customer_subject,idempotency_key)
);
CREATE INDEX return_request_claim_idx ON return_request(next_attempt_at,created_at) WHERE status IN ('PENDING','RUNNING');
CREATE INDEX return_request_order_idx ON return_request(order_id,created_at);

CREATE TABLE return_unit_allocation (
    return_id uuid NOT NULL REFERENCES return_request(return_id),
    order_id uuid NOT NULL,
    sku_id uuid NOT NULL,
    unit_ordinal integer NOT NULL CHECK (unit_ordinal >= 0),
    merchandise_refund_minor bigint NOT NULL CHECK (merchandise_refund_minor >= 0),
    tax_refund_minor bigint NOT NULL CHECK (tax_refund_minor >= 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY(return_id,sku_id,unit_ordinal),
    UNIQUE(order_id,sku_id,unit_ordinal),
    FOREIGN KEY(order_id,sku_id) REFERENCES customer_order_line(order_id,sku_id)
);
