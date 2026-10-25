ARG PYTHON_BASE_IMAGE
FROM ${PYTHON_BASE_IMAGE}
WORKDIR /app
COPY services/relationship-graph/requirements.txt .
RUN pip install --no-cache-dir --requirement requirements.txt
COPY services/relationship-graph/app.py .
COPY contracts/order_events.py .
USER 10001:10001
EXPOSE 8080
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
