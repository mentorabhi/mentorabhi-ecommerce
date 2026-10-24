CREATE TABLE checkout_order_fence(order_id uuid PRIMARY KEY,fence bigint NOT NULL CHECK(fence>0),updated_at timestamptz NOT NULL DEFAULT now());
