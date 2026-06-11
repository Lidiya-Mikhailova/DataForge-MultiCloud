import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
from google.cloud import bigquery

from src.schemas.data_models import Contact, InvalidRecord
from src.warehouse.client import WarehouseClient
from src.warehouse.config import (
    RAW_DATASET,
    CORE_DATASET,
    RAW_CONTACTS_TABLE,
    QUARANTINE_TABLE,
    CORE_CONTACTS_TABLE,
    CONTACTS_SCHEMA,
    QUARANTINE_SCHEMA,
)
from src.warehouse.queries import build_merge_core_query

logger = logging.getLogger(__name__)


class WarehouseLoader:
    def __init__(self, client: WarehouseClient):
        self._client = client
        self._bq = client.bq_client

    def load_valid_to_raw(self, contacts: list[Contact], run_id: str) -> int:
        if not contacts:
            logger.info("No valid contacts to load to raw")
            return 0

        records = []
        for c in contacts:
            d = c.model_dump(mode="json")
            d["processed_at"] = datetime.now(timezone.utc).isoformat()
            d["run_id"] = run_id
            records.append(d)

        df = pd.DataFrame(records)

        table_ref = f"{self._client.project_id}.{RAW_DATASET}.{RAW_CONTACTS_TABLE}"
        job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            schema=CONTACTS_SCHEMA,
            create_disposition=bigquery.CreateDisposition.CREATE_NEVER,
        )

        job = self._bq.load_table_from_dataframe(df, table_ref, job_config=job_config)
        job.result()
        logger.info("Loaded %d valid contacts to %s (run_id=%s)", len(df), table_ref, run_id)
        return len(df)

    def load_invalid_to_quarantine(self, invalid_records: list[InvalidRecord], run_id: str) -> int:
        if not invalid_records:
            logger.info("No invalid records to quarantine")
            return 0

        records = []
        for rec in invalid_records:
            records.append({
                "id": str(uuid.uuid4()),
                "original_data": json.dumps(rec.original_data),
                "error_message": rec.error_message,
                "error_type": rec.error_type,
                "run_id": run_id,
                "quarantined_at": datetime.now(timezone.utc).isoformat(),
            })

        df = pd.DataFrame(records)

        table_ref = f"{self._client.project_id}.{RAW_DATASET}.{QUARANTINE_TABLE}"
        job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            schema=QUARANTINE_SCHEMA,
            create_disposition=bigquery.CreateDisposition.CREATE_NEVER,
        )

        job = self._bq.load_table_from_dataframe(df, table_ref, job_config=job_config)
        job.result()
        logger.info("Loaded %d invalid records to %s (run_id=%s)", len(df), table_ref, run_id)
        return len(df)

    def merge_to_core(self, run_id: str) -> int:
        query = build_merge_core_query(
            project_id=self._client.project_id,
            raw_dataset=RAW_DATASET,
            raw_table=RAW_CONTACTS_TABLE,
            core_dataset=CORE_DATASET,
            core_table=CORE_CONTACTS_TABLE,
        )

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("run_id", "STRING", run_id),
            ],
        )

        job = self._bq.query(query, job_config=job_config)
        result = job.result()
        logger.info("MERGE into %s.%s completed for run_id=%s (modified=%d)",
                    CORE_DATASET, CORE_CONTACTS_TABLE, run_id, result.num_dml_affected_rows or 0)
        return result.num_dml_affected_rows or 0

    def load_raw_df(self, df: pd.DataFrame, table_name: str, dataset: Optional[str] = None,
                    schema: Optional[list] = None) -> int:
        ds = dataset or RAW_DATASET
        table_ref = f"{self._client.project_id}.{ds}.{table_name}"
        job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            schema=schema,
            create_disposition=bigquery.CreateDisposition.CREATE_NEVER,
        )
        job = self._bq.load_table_from_dataframe(df, table_ref, job_config=job_config)
        job.result()
        logger.info("Loaded %d rows to %s", len(df), table_ref)
        return len(df)
