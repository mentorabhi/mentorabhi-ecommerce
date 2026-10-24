CREATE TABLE warehouse(id uuid PRIMARY KEY,name varchar(120) NOT NULL,active boolean NOT NULL DEFAULT true);
INSERT INTO warehouse VALUES('00000000-0000-4000-8000-000000000001','Main warehouse',true);
CREATE TABLE inventory_balance(warehouse_id uuid NOT NULL REFERENCES warehouse(id),sku_id uuid NOT NULL,on_hand bigint NOT NULL DEFAULT 0 CHECK(on_hand>=0),revision bigint NOT NULL DEFAULT 1,PRIMARY KEY(warehouse_id,sku_id));
CREATE TABLE stock_movement(id uuid PRIMARY KEY,warehouse_id uuid NOT NULL REFERENCES warehouse(id),sku_id uuid NOT NULL,delta bigint NOT NULL CHECK(delta<>0),actor varchar(160) NOT NULL,reason varchar(500) NOT NULL,idempotency_key varchar(120) NOT NULL UNIQUE,source varchar(32) NOT NULL DEFAULT 'admin-adjustment',occurred_at timestamptz NOT NULL DEFAULT now());
