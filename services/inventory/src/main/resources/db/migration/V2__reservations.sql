CREATE TABLE inventory_reservation (
  id uuid PRIMARY KEY,
  order_id uuid NOT NULL,
  state varchar(16) NOT NULL CHECK (state IN ('HELD','PROTECTED','COMMITTED','RELEASED','EXPIRED')),
  expires_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(order_id)
);
CREATE TABLE inventory_reservation_line (
  reservation_id uuid NOT NULL REFERENCES inventory_reservation(id),
  warehouse_id uuid NOT NULL REFERENCES warehouse(id),
  sku_id uuid NOT NULL,
  quantity bigint NOT NULL CHECK(quantity > 0),
  PRIMARY KEY(reservation_id, warehouse_id, sku_id)
);
CREATE INDEX inventory_reservation_active_idx ON inventory_reservation(state,expires_at);
