ALTER TABLE payment_operation
  ADD CONSTRAINT payment_operation_known_type CHECK(operation IN ('AUTHORIZE','CAPTURE','VOID','REFUND')),
  ADD CONSTRAINT payment_operation_valid_state CHECK(
    (operation='AUTHORIZE' AND state IN ('AUTHORIZED','DECLINED')) OR
    (operation='CAPTURE' AND state='CAPTURED') OR
    (operation='VOID' AND state='VOIDED') OR
    (operation='REFUND' AND state='REFUNDED')),
  ADD CONSTRAINT payment_refund_positive CHECK(operation<>'REFUND' OR amount_minor>0);

CREATE UNIQUE INDEX payment_one_authorization_per_order ON payment_operation(order_id) WHERE operation='AUTHORIZE';
CREATE UNIQUE INDEX payment_one_capture_per_order ON payment_operation(order_id) WHERE operation='CAPTURE';
CREATE UNIQUE INDEX payment_one_void_per_order ON payment_operation(order_id) WHERE operation='VOID';
