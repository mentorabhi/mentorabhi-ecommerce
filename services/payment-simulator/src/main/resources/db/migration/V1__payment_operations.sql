CREATE TABLE payment_fence(order_id uuid PRIMARY KEY,fence bigint NOT NULL);
CREATE TABLE payment_operation(id bigserial PRIMARY KEY,order_id uuid NOT NULL,operation varchar(16) NOT NULL,operation_key varchar(200) NOT NULL UNIQUE,payload_hash varchar(300) NOT NULL,amount_minor bigint NOT NULL CHECK(amount_minor>=0),currency char(3) NOT NULL,state varchar(16) NOT NULL,fence bigint NOT NULL,created_at timestamptz NOT NULL DEFAULT now());
CREATE INDEX payment_order_idx ON payment_operation(order_id,id);
