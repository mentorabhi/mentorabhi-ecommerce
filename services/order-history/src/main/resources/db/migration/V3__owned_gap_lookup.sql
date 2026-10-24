CREATE INDEX pending_order_event_owner_received_idx ON pending_order_event ((payload->>'customerKey'),received_at);
