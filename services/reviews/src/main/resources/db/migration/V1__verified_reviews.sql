CREATE TABLE product_review (
    id uuid PRIMARY KEY,
    customer_subject varchar(160) NOT NULL,
    order_id uuid NOT NULL,
    product_id uuid NOT NULL,
    sku_id uuid NOT NULL,
    rating smallint NOT NULL CHECK (rating BETWEEN 1 AND 5),
    title varchar(120) NOT NULL,
    body varchar(2000) NOT NULL,
    state varchar(16) NOT NULL DEFAULT 'PENDING' CHECK (state IN ('PENDING','PUBLISHED','REJECTED','HIDDEN')),
    revision bigint NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(customer_subject,order_id,sku_id)
);
CREATE INDEX product_review_public_idx ON product_review(product_id,state,created_at DESC);
CREATE TABLE review_moderation_audit (
    operation_id uuid PRIMARY KEY,
    review_id uuid NOT NULL REFERENCES product_review(id),
    actor_subject varchar(160) NOT NULL,
    previous_state varchar(16) NOT NULL,
    next_state varchar(16) NOT NULL,
    reason varchar(500) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
