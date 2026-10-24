INSERT INTO configuration_category(id,label) VALUES ('returns-policy','Returns policy');
INSERT INTO configuration_setting(key,category,value,value_type,activation_mode,revision)
VALUES ('returns.window-days','returns-policy','30','STRING','OPERATOR_EDITABLE',1);
UPDATE bootstrap_metadata SET schema_version=4,revision=revision+1 WHERE service='configuration';
