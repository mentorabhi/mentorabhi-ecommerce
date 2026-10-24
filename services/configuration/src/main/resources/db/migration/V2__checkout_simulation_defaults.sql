INSERT INTO configuration_setting(key,category,value,value_type,activation_mode,revision) VALUES
  ('checkout.tax.rate-bps','commerce-simulations','1800','STRING','MIGRATION_ONLY',1),
  ('checkout.shipping.INR','commerce-simulations','9900','STRING','MIGRATION_ONLY',1),
  ('checkout.shipping.USD','commerce-simulations','199','STRING','MIGRATION_ONLY',1),
  ('checkout.inventory.reservation-seconds','commerce-simulations','600','STRING','MIGRATION_ONLY',1),
  ('checkout.payment.authorization-mode','commerce-simulations','APPROVE','STRING','MIGRATION_ONLY',1);
UPDATE bootstrap_metadata SET schema_version=2,revision=revision+1 WHERE service='configuration';
