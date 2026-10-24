CREATE TABLE event_inbox (
  event_id uuid PRIMARY KEY,
  payload_hash char(64) NOT NULL,
  aggregate_id uuid NOT NULL,
  aggregate_sequence bigint NOT NULL,
  received_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(aggregate_id,aggregate_sequence)
);
CREATE TABLE pending_order_event (
  event_id uuid PRIMARY KEY,
  payload_hash char(64) NOT NULL,
  aggregate_id uuid NOT NULL,
  aggregate_sequence bigint NOT NULL,
  payload jsonb NOT NULL,
  source_topic varchar(255) NOT NULL,
  source_partition integer NOT NULL,
  source_offset bigint NOT NULL,
  received_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(aggregate_id,aggregate_sequence)
);
CREATE TABLE order_history_projection (
  order_id uuid PRIMARY KEY,
  customer_key char(64) NOT NULL,
  last_sequence bigint NOT NULL,
  state varchar(32) NOT NULL,
  currency char(3),
  total_minor bigint,
  lines jsonb NOT NULL DEFAULT '[]'::jsonb,
  occurred_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX order_history_owner_created_idx ON order_history_projection(customer_key,occurred_at DESC);
CREATE TABLE order_history_state_event (
  event_id uuid PRIMARY KEY REFERENCES event_inbox(event_id),
  order_id uuid NOT NULL REFERENCES order_history_projection(order_id),
  aggregate_sequence bigint NOT NULL,
  event_type varchar(80) NOT NULL,
  state varchar(32) NOT NULL,
  occurred_at timestamptz NOT NULL,
  UNIQUE(order_id,aggregate_sequence)
);
CREATE TABLE order_history_replay_audit (
  operation_id uuid PRIMARY KEY,
  source_coordinate varchar(320) NOT NULL,
  event_id uuid NOT NULL,
  original_payload_hash char(64) NOT NULL,
  replay_payload_hash char(64) NOT NULL,
  operator_subject varchar(160) NOT NULL,
  reason varchar(500) NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
