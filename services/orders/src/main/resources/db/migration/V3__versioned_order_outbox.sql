ALTER TABLE order_outbox
  ADD COLUMN event_id uuid,
  ADD COLUMN event_version integer,
  ADD COLUMN aggregate_sequence bigint,
  ADD COLUMN customer_key varchar(64),
  ADD COLUMN aggregate_type varchar(32);

CREATE TABLE order_event_sequence (
  aggregate_id uuid PRIMARY KEY,
  last_sequence bigint NOT NULL CHECK (last_sequence >= 0)
);

WITH ordered AS (
  SELECT id, row_number() OVER (PARTITION BY aggregate_id ORDER BY id) AS sequence
  FROM order_outbox
)
UPDATE order_outbox target
SET aggregate_sequence=ordered.sequence, event_version=1, aggregate_type='Order'
FROM ordered WHERE target.id=ordered.id;

INSERT INTO order_event_sequence(aggregate_id,last_sequence)
SELECT aggregate_id,max(aggregate_sequence) FROM order_outbox GROUP BY aggregate_id;

CREATE UNIQUE INDEX order_outbox_event_id_uq ON order_outbox(event_id) WHERE event_id IS NOT NULL;
CREATE UNIQUE INDEX order_outbox_aggregate_sequence_uq ON order_outbox(aggregate_id,aggregate_sequence) WHERE aggregate_sequence IS NOT NULL;
