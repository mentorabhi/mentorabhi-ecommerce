CREATE TABLE checkout_quote (
  id uuid PRIMARY KEY,
  request_id uuid NOT NULL UNIQUE,
  customer_subject varchar(160) NOT NULL,
  payload_hash char(64) NOT NULL,
  currency char(3) NOT NULL REFERENCES currency_registry(code),
  currency_revision integer NOT NULL,
  subtotal_minor bigint NOT NULL CHECK(subtotal_minor>=0),
  discount_minor bigint NOT NULL CHECK(discount_minor>=0),
  coupon_id uuid REFERENCES coupon(id),
  coupon_revision integer,
  snapshot jsonb NOT NULL,
  expires_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE coupon_checkout_hold (
  id uuid PRIMARY KEY,
  order_id uuid NOT NULL UNIQUE,
  quote_id uuid NOT NULL REFERENCES checkout_quote(id),
  coupon_id uuid NOT NULL REFERENCES coupon(id),
  customer_subject varchar(160) NOT NULL,
  discount_minor bigint NOT NULL CHECK(discount_minor>0),
  state varchar(16) NOT NULL CHECK(state IN ('HELD','PROTECTED','COMMITTED','RELEASED','EXPIRED')),
  expires_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX coupon_checkout_capacity_idx ON coupon_checkout_hold(coupon_id,state,expires_at);
CREATE INDEX coupon_checkout_owner_idx ON coupon_checkout_hold(coupon_id,customer_subject,state,expires_at);
