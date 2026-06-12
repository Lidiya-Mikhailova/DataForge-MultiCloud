from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Any

from airflow import DAG  # type: ignore[attr-defined]
from airflow.operators.python import PythonOperator

_DAG_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_DAG_DIR)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

logger = logging.getLogger(__name__)

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
}

PATH_PREFIX = "hubspot/contacts"


def _ensure_project_root() -> None:
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)


def _xcom_val(ti: Any, task_id: str, key: str) -> Any:
    try:
        return ti.xcom_pull(task_ids=task_id, key=key)
    except Exception as e:
        logger.warning("XCom pull failed for %s/%s: %s", task_id, key, e)
        return None


def _extract(**context: Any) -> str:
    _ensure_project_root()
    logger.info("Task _extract started")

    try:
        from etl_pipeline import (
            Settings,
            create_hubspot_extractor,
            create_local_loader,
            create_azure_loader,
            stage_extract_and_backup,
        )

        settings = Settings()
        extractor = create_hubspot_extractor(settings)
        loader = (
            create_local_loader(settings)
            if settings.STORAGE_MODE == "local"
            else create_azure_loader(settings)
        )

        run_id, raw_data, blob_name = stage_extract_and_backup(
            settings, extractor, loader, PATH_PREFIX
        )

        ti = context["task_instance"]
        ti.xcom_push(key="run_id", value=run_id)
        ti.xcom_push(key="total_records", value=len(raw_data))
        ti.xcom_push(key="storage_mode", value=settings.STORAGE_MODE)

        logger.info("Extract complete: run_id=%s records=%d", run_id, len(raw_data))
        return run_id

    except Exception as e:
        logger.exception("_extract failed: %s", e)
        raise


def _validate(**context: Any) -> dict[str, int]:
    _ensure_project_root()
    logger.info("Task _validate started")

    ti = context["task_instance"]

    run_id = _xcom_val(ti, "extract", "run_id")
    storage_mode = _xcom_val(ti, "extract", "storage_mode")

    if not run_id:
        msg = "run_id is None — extract task may have failed"
        logger.error(msg)
        raise ValueError(msg)

    try:
        from etl_pipeline import Settings, create_local_loader, create_azure_loader, stage_validate
        from src.transformers.data_processor import HubspotContactTransformer

        settings = Settings()
        loader = (
            create_local_loader(settings)
            if storage_mode == "local"
            else create_azure_loader(settings)
        )
        transformer = HubspotContactTransformer()

        data_dir = os.path.join(settings.LOCAL_DATA_DIR, run_id)
        data_path = os.path.join(data_dir, "raw_data.json")

        if not os.path.exists(data_path):
            logger.error("Raw data file not found: %s", data_path)
            return {"valid": 0, "invalid": 0}

        logger.info("Reading raw data from %s", data_path)
        with open(data_path) as f:
            raw_data = json.load(f)

        logger.info("Validating %d records with Pydantic...", len(raw_data))
        _, valid_count, invalid_count = stage_validate(
            settings, transformer, loader, raw_data, run_id, PATH_PREFIX
        )

        ti.xcom_push(key="valid_count", value=valid_count)
        ti.xcom_push(key="invalid_count", value=invalid_count)

        logger.info("Validate complete: valid=%d invalid=%d", valid_count, invalid_count)
        return {"valid": valid_count, "invalid": invalid_count}

    except Exception as e:
        logger.exception("_validate failed: %s", e)
        raise


def _load_and_transform(**context: Any) -> dict[str, Any]:
    _ensure_project_root()
    logger.info("Task _load_and_transform started")

    ti = context["task_instance"]
    run_id = _xcom_val(ti, "extract", "run_id")

    if not run_id:
        msg = "run_id is None — extract task may have failed"
        logger.error(msg)
        raise ValueError(msg)

    try:
        from etl_pipeline import Settings, create_warehouse, stage_load_to_warehouse, stage_transform
        from src.schemas.data_models import Contact, InvalidRecord, ValidationResult

        settings = Settings()
        data_dir = os.path.join(settings.LOCAL_DATA_DIR, run_id)

        warehouse = create_warehouse(settings)
        if not warehouse:
            logger.warning("Warehouse not configured — load + transform skipped")
            return {"raw_loaded": 0, "quarantined": 0, "dbt_run": False, "core_merged": 0}

        valid_path = os.path.join(data_dir, "valid_contacts.json")
        invalid_path = os.path.join(data_dir, "invalid_records.json")

        valid: list[Contact] = []
        invalid: list[InvalidRecord] = []

        if os.path.exists(valid_path):
            with open(valid_path) as f:
                valid_data = json.load(f)
            for c in valid_data:
                try:
                    valid.append(Contact(**c))
                except Exception as e:
                    logger.warning("Skipping invalid contact record: %s", e)

        if os.path.exists(invalid_path):
            with open(invalid_path) as f:
                invalid_data = json.load(f)
            for r in invalid_data:
                try:
                    invalid.append(InvalidRecord(**r))
                except Exception as e:
                    logger.warning("Skipping invalid record entry: %s", e)

        logger.info(
            "Loaded %d valid contacts, %d invalid records from intermediate files",
            len(valid), len(invalid),
        )

        validation_result = ValidationResult(valid=valid, invalid=invalid)
        raw_loaded, quarantined = stage_load_to_warehouse(warehouse, validation_result, run_id)

        _wc, warehouse_loader = warehouse
        dbt_run, core_merged = stage_transform(settings, warehouse_loader, run_id)

        ti.xcom_push(key="raw_loaded", value=raw_loaded)
        ti.xcom_push(key="quarantined", value=quarantined)
        ti.xcom_push(key="dbt_run", value=str(dbt_run))
        ti.xcom_push(key="core_merged", value=core_merged)

        logger.info(
            "load_and_transform complete: raw=%d quarantine=%d dbt=%s core=%d",
            raw_loaded, quarantined, dbt_run, core_merged,
        )
        return {
            "raw_loaded": raw_loaded,
            "quarantined": quarantined,
            "dbt_run": dbt_run,
            "core_merged": core_merged,
        }

    except Exception as e:
        logger.exception("_load_and_transform failed: %s", e)
        raise


with DAG(
    dag_id="hubspot_etl_pipeline",
    default_args=default_args,
    description="ETL Pipeline: HubSpot -> Azure Blob -> Validation -> BigQuery Warehouse (raw->core->mart)",
    schedule="0 * * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["etl", "hubspot", "azure", "bigquery"],
) as dag:

    extract = PythonOperator(
        task_id="extract",
        python_callable=_extract,
    )

    validate = PythonOperator(
        task_id="validate",
        python_callable=_validate,
    )

    load_and_transform = PythonOperator(
        task_id="load_and_transform",
        python_callable=_load_and_transform,
    )

    extract >> validate >> load_and_transform
