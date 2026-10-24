\getenv catalog_password CATALOG_DB_PASSWORD
\getenv configuration_password CONFIGURATION_DB_PASSWORD
\getenv pricing_password PRICING_DB_PASSWORD
\getenv inventory_password INVENTORY_DB_PASSWORD
\getenv customer_password CUSTOMER_DB_PASSWORD
\getenv orders_password ORDERS_DB_PASSWORD
\getenv payment_password PAYMENT_DB_PASSWORD
\getenv fulfillment_password FULFILLMENT_DB_PASSWORD
SELECT format('CREATE ROLE %I LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD %L', 'supersports_catalog', :'catalog_password') WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='supersports_catalog') \gexec
SELECT format('CREATE ROLE %I LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD %L', 'supersports_configuration', :'configuration_password') WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='supersports_configuration') \gexec
SELECT format('CREATE ROLE %I LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD %L', 'supersports_pricing', :'pricing_password') WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='supersports_pricing') \gexec
SELECT format('CREATE ROLE %I LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD %L', 'supersports_inventory', :'inventory_password') WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='supersports_inventory') \gexec
SELECT format('CREATE ROLE %I LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD %L', 'supersports_customer', :'customer_password') WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='supersports_customer') \gexec
SELECT format('CREATE ROLE %I LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD %L', 'supersports_orders', :'orders_password') WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='supersports_orders') \gexec
SELECT format('CREATE ROLE %I LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD %L', 'supersports_payment', :'payment_password') WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='supersports_payment') \gexec
SELECT format('CREATE ROLE %I LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD %L', 'supersports_fulfillment', :'fulfillment_password') WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='supersports_fulfillment') \gexec
ALTER ROLE supersports_catalog PASSWORD :'catalog_password';
ALTER ROLE supersports_configuration PASSWORD :'configuration_password';
ALTER ROLE supersports_pricing PASSWORD :'pricing_password';
ALTER ROLE supersports_inventory PASSWORD :'inventory_password';
ALTER ROLE supersports_customer PASSWORD :'customer_password';
ALTER ROLE supersports_orders PASSWORD :'orders_password';
ALTER ROLE supersports_payment PASSWORD :'payment_password';
ALTER ROLE supersports_fulfillment PASSWORD :'fulfillment_password';
SELECT format('CREATE DATABASE %I OWNER %I', 'catalog', 'supersports_catalog') WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname='catalog') \gexec
SELECT format('CREATE DATABASE %I OWNER %I', 'configuration', 'supersports_configuration') WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname='configuration') \gexec
SELECT format('CREATE DATABASE %I OWNER %I', 'pricing', 'supersports_pricing') WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname='pricing') \gexec
SELECT format('CREATE DATABASE %I OWNER %I', 'inventory', 'supersports_inventory') WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname='inventory') \gexec
SELECT format('CREATE DATABASE %I OWNER %I', 'customer', 'supersports_customer') WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname='customer') \gexec
SELECT format('CREATE DATABASE %I OWNER %I', 'orders', 'supersports_orders') WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname='orders') \gexec
SELECT format('CREATE DATABASE %I OWNER %I', 'payment', 'supersports_payment') WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname='payment') \gexec
SELECT format('CREATE DATABASE %I OWNER %I', 'fulfillment', 'supersports_fulfillment') WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname='fulfillment') \gexec
REVOKE ALL ON DATABASE catalog, configuration, pricing, inventory, customer, orders, payment, fulfillment FROM PUBLIC;
GRANT CONNECT ON DATABASE catalog TO supersports_catalog;
GRANT CONNECT ON DATABASE configuration TO supersports_configuration;
GRANT CONNECT ON DATABASE pricing TO supersports_pricing;
GRANT CONNECT ON DATABASE inventory TO supersports_inventory;
GRANT CONNECT ON DATABASE customer TO supersports_customer;
GRANT CONNECT ON DATABASE orders TO supersports_orders;
GRANT CONNECT ON DATABASE payment TO supersports_payment;
GRANT CONNECT ON DATABASE fulfillment TO supersports_fulfillment;
