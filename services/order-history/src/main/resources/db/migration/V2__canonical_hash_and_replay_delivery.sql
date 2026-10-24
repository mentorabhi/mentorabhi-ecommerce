ALTER TABLE event_inbox ADD COLUMN canonical_payload_hash char(64);
ALTER TABLE pending_order_event ADD COLUMN canonical_payload_hash char(64);

-- Audit facts are immutable; publication state is separately restartable.
CREATE TABLE order_history_replay_delivery (
  operation_id uuid PRIMARY KEY REFERENCES order_history_replay_audit(operation_id),
  corrected_payload text NOT NULL,
  source_partition integer NOT NULL CHECK(source_partition>=0),
  record_key text,
  published_topic varchar(255),
  published_partition integer,
  published_offset bigint,
  published_at timestamptz
);

CREATE FUNCTION reject_replay_audit_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'Order History replay audit is append-only';
END;
$$;
CREATE TRIGGER replay_audit_append_only BEFORE UPDATE OR DELETE ON order_history_replay_audit
FOR EACH ROW EXECUTE FUNCTION reject_replay_audit_mutation();
