from __future__ import annotations

import csv
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

import pandas as pd
from pydantic_settings import BaseSettings

from src.extractors.hubspot import HubspotDataExtractor
from src.infrastructure.clients.azure_client import AzureBlobClient, MockAzureBlobClient
from src.infrastructure.clients.hubspot_client import HubspotApiClient, MockHubspotClient
from src.infrastructure.clients.local_client import LocalStorageClient
from src.loaders.azure_loader import AzureBlobLoader
from src.loaders.local_loader import LocalStorageLoader
from src.schemas.data_models import Contact, InvalidRecord, ValidationResult
from src.transformers.data_processor import HubspotContactTransformer

if TYPE_CHECKING:
    from src.warehouse import WarehouseClient, WarehouseLoader

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "extra": "ignore"}

    USE_MOCK: bool = False
    HUBSPOT_CSV_PATH: str = "hubspot_raw_mock.csv"
    HUBSPOT_ACCESS_TOKEN: str = ""

    AZURE_STORAGE_CONNECTION_STRING: str = ""
    AZURE_RAW_CONTAINER: str = "raw"
    AZURE_PROCESSED_CONTAINER: str = "processed"
    AZURE_INVALID_CONTAINER: str = "invalid"

    BIGQUERY_PROJECT_ID: str = ""
    GOOGLE_APPLICATION_CREDENTIALS: str = ""

    INIT_WAREHOUSE: bool = True
    STORAGE_MODE: str = "local"
    USE_DBT: bool = False
    DBT_PROJECT_DIR: str = "transform"
    LOCAL_DATA_DIR: str = "data"


class PipelineStats:
    def __init__(
        self,
        run_id: str,
        total_records: int = 0,
        valid_records: int = 0,
        invalid_records: int = 0,
        raw_loaded: int = 0,
        quarantined: int = 0,
        core_merged: int = 0,
        dbt_run: bool = False,
    ) -> None:
        self.run_id = run_id
        self.total_records = total_records
        self.valid_records = valid_records
        self.invalid_records = invalid_records
        self.raw_loaded = raw_loaded
        self.quarantined = quarantined
        self.core_merged = core_merged
        self.dbt_run = dbt_run


def create_run_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + str(uuid.uuid4())[:8]


def _ensure_data_dir(settings: Settings, run_id: str) -> str:
    data_dir = os.path.join(settings.LOCAL_DATA_DIR, run_id)
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def _save_intermediate(data: Any, path: str) -> str:
    with open(path, "w") as f:
        json.dump(data, f, default=str)
    return path


def _load_intermediate(path: str) -> Any:
    with open(path) as f:
        return json.load(f)


def create_hubspot_extractor(settings: Settings) -> HubspotDataExtractor:
    if settings.USE_MOCK:
        client: HubspotApiClient | MockHubspotClient = MockHubspotClient()
    else:
        client = HubspotApiClient(settings.HUBSPOT_ACCESS_TOKEN)
    return HubspotDataExtractor(client)


def read_csv_data(csv_path: str) -> list[dict]:
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    logger.info("Read %d records from %s", len(rows), csv_path)
    return rows


def create_azure_loader(settings: Settings) -> AzureBlobLoader:
    if settings.USE_MOCK:
        blob_client: AzureBlobClient | MockAzureBlobClient = MockAzureBlobClient()
    else:
        blob_client = AzureBlobClient(settings.AZURE_STORAGE_CONNECTION_STRING)
    return AzureBlobLoader(
        blob_client,
        raw_container=settings.AZURE_RAW_CONTAINER,
        processed_container=settings.AZURE_PROCESSED_CONTAINER,
        invalid_container=settings.AZURE_INVALID_CONTAINER,
    )


def create_local_loader(settings: Settings) -> LocalStorageLoader:
    client = LocalStorageClient(data_dir=settings.LOCAL_DATA_DIR)
    return LocalStorageLoader(
        client,
        raw_container=settings.AZURE_RAW_CONTAINER,
        processed_container=settings.AZURE_PROCESSED_CONTAINER,
        invalid_container=settings.AZURE_INVALID_CONTAINER,
    )


def create_warehouse(settings: Settings) -> Optional[tuple[WarehouseClient, WarehouseLoader]]:
    if not settings.BIGQUERY_PROJECT_ID:
        logger.warning("BIGQUERY_PROJECT_ID not configured, skipping warehouse setup")
        return None
    if not settings.GOOGLE_APPLICATION_CREDENTIALS:
        logger.warning("GOOGLE_APPLICATION_CREDENTIALS not set, skipping warehouse setup")
        return None
    if not os.path.exists(settings.GOOGLE_APPLICATION_CREDENTIALS):
        logger.warning("Credentials file not found: %s, skipping warehouse setup",
                       settings.GOOGLE_APPLICATION_CREDENTIALS)
        return None

    from src.warehouse import WarehouseClient, WarehouseLoader

    client = WarehouseClient(
        project_id=settings.BIGQUERY_PROJECT_ID,
        credentials_path=settings.GOOGLE_APPLICATION_CREDENTIALS,
    )

    if settings.INIT_WAREHOUSE:
        client.initialize()

    loader = WarehouseLoader(client)
    return client, loader


def run_dbt(settings: Settings) -> bool:
    dbt_dir = settings.DBT_PROJECT_DIR
    if not os.path.isdir(dbt_dir):
        logger.warning("dbt project dir '%s' not found, skipping dbt", dbt_dir)
        return False

    import subprocess
    env = os.environ.copy()
    env["BIGQUERY_PROJECT_ID"] = settings.BIGQUERY_PROJECT_ID
    env["GOOGLE_APPLICATION_CREDENTIALS"] = settings.GOOGLE_APPLICATION_CREDENTIALS

    cmds = [
        ["dbt", "deps"],
        ["dbt", "run", "--profiles-dir", "."],
        ["dbt", "test", "--profiles-dir", "."],
    ]
    for cmd in cmds:
        logger.info("dbt: running %s", " ".join(cmd))
        result = subprocess.run(
            cmd,
            cwd=dbt_dir,
            env=env,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.error("dbt command failed: %s\nstdout: %s\nstderr: %s",
                         " ".join(cmd), result.stdout[-2000:], result.stderr[-2000:])
            return False
        if result.stdout:
            for line in result.stdout.strip().splitlines():
                logger.info("dbt: %s", line)
    logger.info("dbt: all stages completed successfully")
    return True


def _safe_merge_to_core(warehouse_loader: WarehouseLoader, run_id: str) -> int:
    try:
        return warehouse_loader.merge_to_core(run_id)
    except Exception as e:
        logger.warning("MERGE to core skipped (non-fatal): %s", e)
        return 0

def stage_extract_and_backup(
    settings: Settings,
    extractor: HubspotDataExtractor,
    loader: AzureBlobLoader | LocalStorageLoader,
    path_prefix: str = "hubspot/contacts",
) -> tuple[str, list[dict], str]:
    run_id = create_run_id()
    logger.info("[STAGE 1] Extracting data from HubSpot (run_id: %s)...", run_id)
    if settings.USE_MOCK:
        raw_data = extractor.extract()
    else:
        raw_data = read_csv_data(settings.HUBSPOT_CSV_PATH)
    logger.info("Extracted %d raw records", len(raw_data))

    logger.info("[STAGE 2] Backing up raw data...")
    blob_name = f"{path_prefix}/{run_id}/raw_batch.json"
    loader.save_raw(raw_data, blob_name)
    logger.info("Raw data saved to '%s/%s'", loader.raw_container, blob_name)

    data_dir = _ensure_data_dir(settings, run_id)
    _save_intermediate(raw_data, os.path.join(data_dir, "raw_data.json"))

    return run_id, raw_data, blob_name


def stage_validate(
    settings: Settings,
    transformer: HubspotContactTransformer,
    loader: AzureBlobLoader | LocalStorageLoader,
    raw_data: list[dict],
    run_id: str,
    path_prefix: str = "hubspot/contacts",
) -> tuple[ValidationResult, int, int]:
    logger.info("[STAGE 3] Validating data with Pydantic...")

    if not raw_data:
        logger.warning("No raw data to validate")
        empty = ValidationResult(valid=[], invalid=[])
        return empty, 0, 0

    validation_result: ValidationResult = transformer.transform(raw_data)
    logger.info("Validation complete: %d valid, %d invalid",
                len(validation_result.valid), len(validation_result.invalid))

    data_dir = _ensure_data_dir(settings, run_id)
    _save_intermediate(
        [c.model_dump(mode="json") for c in validation_result.valid],
        os.path.join(data_dir, "valid_contacts.json"),
    )
    _save_intermediate(
        [r.model_dump(mode="json") for r in validation_result.invalid],
        os.path.join(data_dir, "invalid_records.json"),
    )

    if validation_result.invalid:
        try:
            logger.info("[STAGE 8] Archiving invalid data (%d records)...", len(validation_result.invalid))
            invalid_data = [
                {"original_data": r.original_data, "error_message": r.error_message, "error_type": r.error_type}
                for r in validation_result.invalid
            ]
            invalid_blob_name = f"{path_prefix}/{run_id}/invalid_batch.json"
            loader.save_invalid(invalid_data, invalid_blob_name)
            logger.info("Invalid data saved to '%s/%s'", loader.invalid_container, invalid_blob_name)
        except Exception as e:
            logger.warning("Failed to archive invalid data (non-fatal): %s", e)

    return validation_result, len(validation_result.valid), len(validation_result.invalid)


def stage_load_to_warehouse(
    warehouse: tuple[WarehouseClient, WarehouseLoader],
    validation_result: ValidationResult,
    run_id: str,
) -> tuple[int, int]:
    _warehouse_client, warehouse_loader = warehouse
    raw_loaded = 0
    quarantined = 0

    if validation_result.valid:
        logger.info("[STAGE 4] Loading valid data to BigQuery RAW...")
        for contact in validation_result.valid:
            contact.run_id = run_id
            contact.processed_at = datetime.now(timezone.utc)
        raw_loaded = warehouse_loader.load_valid_to_raw(validation_result.valid, run_id)
        logger.info("Loaded %d valid contacts to BigQuery RAW", raw_loaded)

    if validation_result.invalid:
        logger.info("[STAGE 5] Loading invalid records to BigQuery QUARANTINE...")
        quarantined = warehouse_loader.load_invalid_to_quarantine(validation_result.invalid, run_id)
        logger.info("Quarantined %d invalid records in BigQuery", quarantined)

    return raw_loaded, quarantined


def stage_transform(
    settings: Settings,
    warehouse_loader: WarehouseLoader,
    run_id: str,
) -> tuple[bool, int]:
    dbt_run = False
    core_merged = 0

    if settings.USE_DBT:
        logger.info("[STAGE 6] Running dbt transformations...")
        dbt_run = run_dbt(settings)
        if not dbt_run:
            logger.warning("dbt failed, falling back to Python MERGE")
            core_merged = _safe_merge_to_core(warehouse_loader, run_id)
        else:
            core_merged = -1
    else:
        logger.info("[STAGE 6] MERGING raw -> core via Python...")
        core_merged = _safe_merge_to_core(warehouse_loader, run_id)

    logger.info("[STAGE 7] BigQuery warehouse update complete.")
    return dbt_run, core_merged

def run_etl_pipeline(
    extractor: HubspotDataExtractor,
    transformer: HubspotContactTransformer,
    azure_loader: AzureBlobLoader,
    warehouse: Optional[tuple[WarehouseClient, WarehouseLoader]],
    settings: Settings,
    path_prefix: str = "hubspot/contacts",
) -> PipelineStats:
    run_id, raw_data, _ = stage_extract_and_backup(settings, extractor, azure_loader, path_prefix)
    stats = PipelineStats(run_id=run_id, total_records=len(raw_data))

    validation_result, stats.valid_records, stats.invalid_records = stage_validate(
        settings, transformer, azure_loader, raw_data, run_id, path_prefix
    )

    if warehouse:
        stats.raw_loaded, stats.quarantined = stage_load_to_warehouse(warehouse, validation_result, run_id)
        if validation_result.valid:
            _wc, warehouse_loader = warehouse
            stats.dbt_run, stats.core_merged = stage_transform(settings, warehouse_loader, run_id)

    logger.info("=" * 60)
    logger.info("ETL Pipeline completed (run_id: %s)", run_id)
    logger.info("  Total: %d | Valid: %d | Invalid: %d | Raw: %d | Quarantine: %d | Core: %s%s",
                stats.total_records, stats.valid_records, stats.invalid_records,
                stats.raw_loaded, stats.quarantined,
                "dbt" if stats.dbt_run else str(stats.core_merged),
                "" if stats.dbt_run else " rows")
    logger.info("=" * 60)

    return stats


def main() -> None:
    settings = Settings()
    logger.info("Starting ETL pipeline with configuration:")
    logger.info("  USE_MOCK: %s", settings.USE_MOCK)
    logger.info("  Azure containers: raw=%s, processed=%s, invalid=%s",
                settings.AZURE_RAW_CONTAINER,
                settings.AZURE_PROCESSED_CONTAINER,
                settings.AZURE_INVALID_CONTAINER)
    logger.info("  BigQuery project: %s", settings.BIGQUERY_PROJECT_ID)
    logger.info("  Warehouse datasets: crm_data_raw, crm_data_core, crm_data_mart")
    logger.info("  Transformation engine: %s", "dbt" if settings.USE_DBT else "Python MERGE (legacy)")

    extractor = create_hubspot_extractor(settings)
    transformer = HubspotContactTransformer()

    if settings.STORAGE_MODE == "local":
        logger.info("  STORAGE_MODE: local (DuckDB + Parquet)")
        loader = create_local_loader(settings)
    else:
        logger.info("  STORAGE_MODE: cloud (Azure Blob Storage)")
        loader = create_azure_loader(settings)

    warehouse = create_warehouse(settings)

    stats = run_etl_pipeline(
        extractor=extractor,
        transformer=transformer,
        azure_loader=loader,
        warehouse=warehouse,
        settings=settings,
    )

    if hasattr(loader, "close"):
        loader.close()

    logger.info("Pipeline finished with run_id: %s", stats.run_id)


if __name__ == "__main__":
    main()
