ARG SUPERSET_BASE_IMAGE
FROM ${SUPERSET_BASE_IMAGE}
USER root
RUN pip install --no-cache-dir 'trino[sqlalchemy]==0.340.0'
USER superset
