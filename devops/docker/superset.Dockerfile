FROM apache/superset:6.1.0
USER root
RUN pip install --no-cache-dir 'trino[sqlalchemy]==0.340.0'
USER superset
