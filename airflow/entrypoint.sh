#!/usr/bin/env bash
set -e

AIRFLOW_HOME="${AIRFLOW_HOME:-/opt/airflow}"

airflow db migrate

airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    --password admin \
    2>/dev/null || echo "✓ Admin user already exists"

airflow connections create-or-update \
    --conn-id bigquery_default \
    --conn-type google_cloud_platform \
    --conn-extra "{\"project\": \"${BIGQUERY_PROJECT_ID}\", \"key_path\": \"${GOOGLE_APPLICATION_CREDENTIALS}\"}" \
    2>/dev/null || echo "⚠ BigQuery connection skipped"

airflow connections create-or-update \
    --conn-id azure_blob_default \
    --conn-type azure_blob_storage \
    --conn-extra "{\"connection_string\": \"${AZURE_STORAGE_CONNECTION_STRING}\"}" \
    2>/dev/null || echo "⚠ Azure connection skipped"

airflow variables set BIGQUERY_PROJECT_ID "${BIGQUERY_PROJECT_ID}" 2>/dev/null || true
airflow variables set AZURE_RAW_CONTAINER "${AZURE_RAW_CONTAINER:-raw}" 2>/dev/null || true
airflow variables set AZURE_PROCESSED_CONTAINER "${AZURE_PROCESSED_CONTAINER:-processed}" 2>/dev/null || true
airflow variables set AZURE_INVALID_CONTAINER "${AZURE_INVALID_CONTAINER:-invalid}" 2>/dev/null || true
airflow variables set STORAGE_MODE "${STORAGE_MODE:-local}" 2>/dev/null || true
airflow variables set INIT_WAREHOUSE "${INIT_WAREHOUSE:-true}" 2>/dev/null || true

mkdir -p "${AIRFLOW_HOME}/logs" "${AIRFLOW_HOME}/dags"

exec airflow "$@"
