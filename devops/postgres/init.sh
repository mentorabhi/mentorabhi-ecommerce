#!/usr/bin/env bash
set -euo pipefail
psql --username "$POSTGRES_USER" --dbname postgres --set ON_ERROR_STOP=1 \
  --set catalog_password="$CATALOG_DB_PASSWORD" \
  --set configuration_password="$CONFIGURATION_DB_PASSWORD" \
  --set identity_password="$IDENTITY_DB_PASSWORD" <<'SQL'
CREATE ROLE supersports_catalog LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD :'catalog_password';
CREATE ROLE supersports_configuration LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD :'configuration_password';
CREATE ROLE supersports_identity LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD :'identity_password';
CREATE DATABASE catalog OWNER supersports_catalog;
CREATE DATABASE configuration OWNER supersports_configuration;
CREATE DATABASE identity OWNER supersports_identity;
REVOKE ALL ON DATABASE catalog FROM PUBLIC;
REVOKE ALL ON DATABASE configuration FROM PUBLIC;
REVOKE ALL ON DATABASE identity FROM PUBLIC;
REVOKE CONNECT ON DATABASE postgres FROM PUBLIC;
REVOKE CONNECT ON DATABASE template1 FROM PUBLIC;
GRANT CONNECT ON DATABASE catalog TO supersports_catalog;
GRANT CONNECT ON DATABASE configuration TO supersports_configuration;
GRANT CONNECT ON DATABASE identity TO supersports_identity;
SQL
