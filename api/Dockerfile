FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY api/ /app/
COPY rules/ /app/rules/
COPY samples/ /app/samples/
COPY tests/fixtures/ /app/tests/fixtures/

ENV PYTHONPATH=/app
ENV ARTIFACTS_DIR=/app/artifacts

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
