CREATE TABLE customer_profile (
    subject TEXT PRIMARY KEY CHECK (length(subject) BETWEEN 1 AND 200),
    full_name TEXT NOT NULL DEFAULT '' CHECK (length(full_name) <= 200),
    phone TEXT NOT NULL DEFAULT '' CHECK (length(phone) <= 40),
    line1 TEXT NOT NULL DEFAULT '' CHECK (length(line1) <= 200),
    line2 TEXT NOT NULL DEFAULT '' CHECK (length(line2) <= 200),
    city TEXT NOT NULL DEFAULT '' CHECK (length(city) <= 100),
    state TEXT NOT NULL DEFAULT '' CHECK (length(state) <= 100),
    postal_code TEXT NOT NULL DEFAULT '' CHECK (length(postal_code) <= 10),
    country CHAR(2) NOT NULL DEFAULT 'IN' CHECK (country = 'IN'),
    revision INTEGER NOT NULL DEFAULT 1 CHECK (revision > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE cart_item (
    subject TEXT NOT NULL REFERENCES customer_profile(subject) ON DELETE CASCADE,
    sku_id UUID NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity BETWEEN 1 AND 99),
    revision INTEGER NOT NULL DEFAULT 1 CHECK (revision > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (subject, sku_id)
);
CREATE INDEX cart_item_subject_updated ON cart_item(subject, updated_at);

CREATE TABLE wishlist_item (
    subject TEXT NOT NULL REFERENCES customer_profile(subject) ON DELETE CASCADE,
    sku_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (subject, sku_id)
);
