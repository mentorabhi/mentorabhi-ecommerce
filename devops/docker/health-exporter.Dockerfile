ARG PYTHON_BASE_IMAGE
FROM ${PYTHON_BASE_IMAGE}
WORKDIR /app
COPY services/health-exporter/app.py .
USER 10001:10001
ENV HEALTH_TARGETS_FILE=/etc/supersports/health-targets.json
EXPOSE 9108
CMD ["python", "/app/app.py"]
