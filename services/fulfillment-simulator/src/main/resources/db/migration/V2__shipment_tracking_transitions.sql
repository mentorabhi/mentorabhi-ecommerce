ALTER TABLE shipment
    ADD COLUMN revision bigint NOT NULL DEFAULT 0,
    ADD COLUMN estimated_delivery_at timestamptz;

UPDATE shipment SET estimated_delivery_at=created_at + interval '4 days';
ALTER TABLE shipment ALTER COLUMN estimated_delivery_at SET NOT NULL;
ALTER TABLE shipment ADD CONSTRAINT shipment_state_allowed
    CHECK (state IN ('SCHEDULED','HANDED_OFF','IN_TRANSIT','DELIVERED','CANCEL_CLAIMED','CANCELLED','MANUAL_REVIEW'));
ALTER TABLE shipment ADD CONSTRAINT shipment_revision_nonnegative CHECK (revision >= 0);

CREATE TABLE shipment_transition_audit (
    operation_id uuid PRIMARY KEY,
    order_id uuid NOT NULL REFERENCES shipment(order_id),
    request_hash char(64) NOT NULL,
    previous_state varchar(24) NOT NULL,
    next_state varchar(24) NOT NULL,
    previous_revision bigint NOT NULL,
    next_revision bigint NOT NULL,
    actor_subject varchar(160) NOT NULL,
    reason varchar(500) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(order_id,next_revision)
);

CREATE INDEX shipment_transition_order_idx
    ON shipment_transition_audit(order_id, next_revision);
