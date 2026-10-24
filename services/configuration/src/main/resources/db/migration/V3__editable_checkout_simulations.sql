ALTER TABLE configuration_setting DROP CONSTRAINT configuration_setting_activation_mode_check;
ALTER TABLE configuration_setting ADD CONSTRAINT configuration_setting_activation_mode_check
    CHECK (activation_mode IN ('MIGRATION_ONLY','OPERATOR_EDITABLE'));
UPDATE configuration_setting SET activation_mode='OPERATOR_EDITABLE' WHERE key LIKE 'checkout.%';
CREATE TABLE configuration_setting_audit (
  id bigserial PRIMARY KEY,
  setting_key varchar(128) NOT NULL REFERENCES configuration_setting(key),
  old_value text NOT NULL,
  new_value text NOT NULL,
  old_revision bigint NOT NULL,
  new_revision bigint NOT NULL,
  actor varchar(160) NOT NULL,
  occurred_at timestamptz NOT NULL DEFAULT now()
);
UPDATE bootstrap_metadata SET schema_version=3,revision=revision+1 WHERE service='configuration';
