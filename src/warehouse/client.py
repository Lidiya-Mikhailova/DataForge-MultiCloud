import logging
from typing import Optional

from google.cloud import bigquery

from src.warehouse.config import (
    RAW_DATASET,
    CORE_DATASET,
    MART_DATASET,
    TABLE_DEFINITIONS,
)
from src.warehouse.queries import build_all_mart_views

logger = logging.getLogger(__name__)


class WarehouseClient:
    def __init__(self, project_id: str, credentials_path: str):
        self.project_id = project_id
        self.client = bigquery.Client.from_service_account_json(credentials_path)

    def initialize(self) -> None:
        self._create_datasets()
        self._create_tables()
        self._create_mart_views()
        logger.info("Warehouse initialized: datasets=%s, core tables=%d, mart views=%d",
                    [RAW_DATASET, CORE_DATASET, MART_DATASET],
                    len([t for t in TABLE_DEFINITIONS if TABLE_DEFINITIONS[t].dataset_id != MART_DATASET]),
                    len(build_all_mart_views(self.project_id, CORE_DATASET, "core_contacts", RAW_DATASET, "contacts_quarantine")))

    def _create_datasets(self) -> None:
        for dataset_id in (RAW_DATASET, CORE_DATASET, MART_DATASET):
            ref = bigquery.Dataset(f"{self.project_id}.{dataset_id}")
            ref.description = {
                RAW_DATASET: "Raw/staging ingestion layer — append-only landing tables",
                CORE_DATASET: "Core warehouse layer — deduplicated, partitioned, cleaned tables",
                MART_DATASET: "BI-ready analytical views for dashboards and reporting",
            }.get(dataset_id, "")
            ref.labels = {"layer": {
                RAW_DATASET: "raw",
                CORE_DATASET: "core",
                MART_DATASET: "mart",
            }.get(dataset_id, "unknown")}
            self.client.create_dataset(ref, exists_ok=True)
            logger.info("Dataset ensured: %s.%s", self.project_id, dataset_id)

    def _create_tables(self) -> None:
        for cfg in TABLE_DEFINITIONS.values():
            ref = bigquery.Table(f"{self.project_id}.{cfg.dataset_id}.{cfg.table_id}", schema=cfg.schema_fields)
            ref.description = cfg.description
            ref.labels = {"table_type": cfg.dataset_id.replace("crm_data_", "")}

            if cfg.partition_field:
                ref.time_partitioning = bigquery.TimePartitioning(
                    field=cfg.partition_field,
                    type_=bigquery.TimePartitioningType.DAY,
                )
            else:
                ref.time_partitioning = bigquery.TimePartitioning(
                    type_=bigquery.TimePartitioningType.DAY,
                )

            if cfg.clustering_fields:
                ref.clustering_fields = cfg.clustering_fields

            self.client.create_table(ref, exists_ok=True)
            logger.info("Table ensured: %s.%s.%s (partition=%s, cluster=%s)",
                        self.project_id, cfg.dataset_id, cfg.table_id,
                        cfg.partition_field or "ingestion_date",
                        cfg.clustering_fields or "none")

    def _create_mart_views(self) -> None:
        from src.warehouse.config import CORE_CONTACTS_TABLE, QUARANTINE_TABLE
        views = build_all_mart_views(
            project_id=self.project_id,
            core_dataset=CORE_DATASET,
            core_table=CORE_CONTACTS_TABLE,
            raw_dataset=RAW_DATASET,
            quarantine_table=QUARANTINE_TABLE,
        )
        for view_name, ddl in views:
            try:
                self.client.query(ddl).result()
                logger.info("View ensured: %s.%s.%s", self.project_id, MART_DATASET, view_name)
            except Exception as e:
                logger.warning("Failed to create view %s: %s", view_name, e)

    def execute_query(self, query: str, params: Optional[dict[str, str]] = None) -> bigquery.table.RowIterator:
        job_config = bigquery.QueryJobConfig()
        if params:
            job_config.query_parameters = [
                bigquery.ScalarQueryParameter(k, "STRING", v) for k, v in params.items()
            ]
        return self.client.query(query, job_config=job_config).result()

    @property
    def bq_client(self) -> bigquery.Client:
        return self.client
