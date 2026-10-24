CREATE TABLE fulfillment_fence(order_id uuid PRIMARY KEY,fence bigint NOT NULL);
CREATE TABLE shipment(id bigserial PRIMARY KEY,order_id uuid NOT NULL UNIQUE,operation_key varchar(200) NOT NULL UNIQUE,tracking_id varchar(24) NOT NULL UNIQUE,fence bigint NOT NULL,state varchar(24) NOT NULL,created_at timestamptz NOT NULL DEFAULT now());
