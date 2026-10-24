CREATE TABLE checkout_request (
  id uuid PRIMARY KEY,
  customer_subject varchar(160) NOT NULL,
  idempotency_key varchar(120) NOT NULL,
  payload_hash char(64) NOT NULL,
  status varchar(20) NOT NULL CHECK(status IN ('VALIDATING','ACCEPTED','REJECTED')),
  validation_lease_until timestamptz NOT NULL,
  error_code varchar(80),
  order_id uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(customer_subject,idempotency_key)
);
CREATE TABLE customer_order (
  id uuid PRIMARY KEY,
  checkout_request_id uuid NOT NULL UNIQUE REFERENCES checkout_request(id),
  customer_subject varchar(160) NOT NULL,
  state varchar(32) NOT NULL,
  currency char(3) NOT NULL,
  subtotal_minor bigint NOT NULL CHECK(subtotal_minor>=0),
  discount_minor bigint NOT NULL CHECK(discount_minor>=0),
  tax_minor bigint NOT NULL CHECK(tax_minor>=0),
  shipping_minor bigint NOT NULL CHECK(shipping_minor>=0),
  total_minor bigint NOT NULL CHECK(total_minor>=0),
  address_snapshot jsonb NOT NULL,
  quote_snapshot jsonb NOT NULL,
  configuration_revision bigint NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX customer_order_owner_idx ON customer_order(customer_subject,created_at DESC);
CREATE TABLE customer_order_line (
  order_id uuid NOT NULL REFERENCES customer_order(id),
  sku_id uuid NOT NULL,
  product_id uuid NOT NULL,
  product_title varchar(240) NOT NULL,
  quantity integer NOT NULL CHECK(quantity>0),
  unit_price_minor bigint NOT NULL CHECK(unit_price_minor>=0),
  discount_minor bigint NOT NULL CHECK(discount_minor>=0),
  line_total_minor bigint NOT NULL CHECK(line_total_minor>=0),
  currency char(3) NOT NULL,
  PRIMARY KEY(order_id,sku_id)
);
CREATE TABLE checkout_saga (
  order_id uuid PRIMARY KEY REFERENCES customer_order(id),
  state varchar(32) NOT NULL,
  current_step varchar(48) NOT NULL,
  attempt integer NOT NULL DEFAULT 0,
  next_attempt_at timestamptz NOT NULL DEFAULT now(),
  lease_owner varchar(160),
  lease_until timestamptz,
  fence bigint NOT NULL DEFAULT 0,
  last_error_code varchar(80),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE checkout_saga_step (
  id bigserial PRIMARY KEY,
  order_id uuid NOT NULL REFERENCES customer_order(id),
  step varchar(48) NOT NULL,
  operation_key varchar(200) NOT NULL UNIQUE,
  state varchar(20) NOT NULL,
  attempt integer NOT NULL DEFAULT 0,
  result jsonb,
  error_code varchar(80),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(order_id,step)
);
CREATE TABLE order_outbox (
  id bigserial PRIMARY KEY,
  aggregate_id uuid NOT NULL,
  event_type varchar(80) NOT NULL,
  payload jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  published_at timestamptz
);
