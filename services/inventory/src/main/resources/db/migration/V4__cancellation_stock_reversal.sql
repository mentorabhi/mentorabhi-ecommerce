ALTER TABLE inventory_reservation DROP CONSTRAINT inventory_reservation_state_check;
ALTER TABLE inventory_reservation ADD CONSTRAINT inventory_reservation_state_check
    CHECK (state IN ('HELD','PROTECTED','COMMITTED','RELEASED','EXPIRED','CANCELLED'));
ALTER TABLE inventory_reservation ADD COLUMN cancellation_operation_id uuid UNIQUE;
