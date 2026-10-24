\getenv catalog_password CATALOG_DB_PASSWORD
\getenv configuration_password CONFIGURATION_DB_PASSWORD
\getenv pricing_password PRICING_DB_PASSWORD
\getenv inventory_password INVENTORY_DB_PASSWORD
SELECT format('CREATE ROLE %I LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD %L', 'supersports_catalog', :'catalog_password') WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='supersports_catalog') \gexec
SELECT format('CREATE ROLE %I LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD %L', 'supersports_configuration', :'configuration_password') WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='supersports_configuration') \gexec
SELECT format('CREATE ROLE %I LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD %L', 'supersports_pricing', :'pricing_password') WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='supersports_pricing') \gexec
SELECT format('CREATE ROLE %I LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD %L', 'supersports_inventory', :'inventory_password') WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='supersports_inventory') \gexec
ALTER ROLE supersports_catalog PASSWORD :'catalog_password';
ALTER ROLE supersports_configuration PASSWORD :'configuration_password';
ALTER ROLE supersports_pricing PASSWORD :'pricing_password';
ALTER ROLE supersports_inventory PASSWORD :'inventory_password';
SELECT format('CREATE DATABASE %I OWNER %I', 'catalog', 'supersports_catalog') WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname='catalog') \gexec
SELECT format('CREATE DATABASE %I OWNER %I', 'configuration', 'supersports_configuration') WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname='configuration') \gexec
SELECT format('CREATE DATABASE %I OWNER %I', 'pricing', 'supersports_pricing') WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname='pricing') \gexec
SELECT format('CREATE DATABASE %I OWNER %I', 'inventory', 'supersports_inventory') WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname='inventory') \gexec
REVOKE ALL ON DATABASE catalog, configuration, pricing, inventory FROM PUBLIC;
GRANT CONNECT ON DATABASE catalog TO supersports_catalog;
GRANT CONNECT ON DATABASE configuration TO supersports_configuration;
GRANT CONNECT ON DATABASE pricing TO supersports_pricing;
GRANT CONNECT ON DATABASE inventory TO supersports_inventory;
