ARG SUPERSET_BASE_IMAGE
FROM ${SUPERSET_BASE_IMAGE}
USER root
RUN /app/.venv/bin/python -c "import re; from pathlib import Path; Path('/tmp/superset-constraints.txt').write_text('\n'.join(line for line in Path('/app/requirements/base.txt').read_text().splitlines() if re.match(r'^[A-Za-z0-9][A-Za-z0-9_.-]*==', line)) + '\n')" \
    && uv pip install --python /app/.venv/bin/python --constraint /tmp/superset-constraints.txt 'trino[sqlalchemy]==0.340.0' 'lz4==4.4.5' 'orjson==3.13.0' 'tzlocal==5.4.5' \
    && /app/.venv/bin/python -c "import sqlalchemy, trino; assert sqlalchemy.__version__ == '1.4.54'; assert trino.__version__ == '0.340.0'"
USER superset
