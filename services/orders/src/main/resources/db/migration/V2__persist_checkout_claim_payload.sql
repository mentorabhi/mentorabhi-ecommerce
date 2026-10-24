ALTER TABLE checkout_request ADD COLUMN payload jsonb NOT NULL DEFAULT '{}'::jsonb;
