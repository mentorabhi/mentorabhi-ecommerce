ALTER TABLE shipment
    ADD COLUMN cancel_claim_operation_id uuid UNIQUE,
    ADD COLUMN cancellation_operation_id uuid UNIQUE;

CREATE TABLE shipment_cancellation_audit (
    operation_id uuid PRIMARY KEY,
    order_id uuid NOT NULL REFERENCES shipment(order_id),
    action varchar(24) NOT NULL CHECK (action IN ('CLAIM','CANCEL')),
    previous_state varchar(24) NOT NULL,
    next_state varchar(24) NOT NULL,
    previous_revision bigint NOT NULL,
    next_revision bigint NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(order_id, action)
);
