# Catalog fixtures

The manifest contains only synthetic products and local prices in integer minor units. `import.py` reads this checked-in source and calls local APIs with the synthetic catalog and inventory operators. It uses stable product/SKU codes and idempotency keys so a repeated run reconciles catalog and price fields and replays initial stock adjustments. It never reads or changes database tables directly.

Run after the local stack is healthy:

```sh
.venv/bin/python data/pipelines/catalog-fixtures/import.py
```

Credentials are loaded from the ignored `devops/.local/bootstrap.env`; tokens stay in memory. Product SVGs are packaged in `apps/storefront/public/`.
