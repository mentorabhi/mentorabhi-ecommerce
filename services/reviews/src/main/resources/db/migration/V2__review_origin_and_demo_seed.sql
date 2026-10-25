-- Existing rows remain real, purchase-owned customer reviews, with states/audits intact.
ALTER TABLE product_review ADD COLUMN origin varchar(16) NOT NULL DEFAULT 'CUSTOMER';
ALTER TABLE product_review ALTER COLUMN customer_subject DROP NOT NULL;
ALTER TABLE product_review ALTER COLUMN order_id DROP NOT NULL;
ALTER TABLE product_review ALTER COLUMN sku_id DROP NOT NULL;
ALTER TABLE product_review ADD CONSTRAINT product_review_origin_ownership CHECK (
    (origin = 'CUSTOMER' AND customer_subject IS NOT NULL AND order_id IS NOT NULL AND sku_id IS NOT NULL)
 OR (origin = 'DEMO' AND customer_subject IS NULL AND order_id IS NULL AND sku_id IS NULL AND rating BETWEEN 3 AND 5)
);
-- Persist successful operation input independently of subsequent review moderation.
CREATE TABLE review_demo_seed_operation (
    operation_id uuid PRIMARY KEY,
    actor_subject varchar(160) NOT NULL,
    product_ids text NOT NULL,
    reviews_per_product smallint NOT NULL CHECK (reviews_per_product IN (3,4)),
    created_count integer NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
