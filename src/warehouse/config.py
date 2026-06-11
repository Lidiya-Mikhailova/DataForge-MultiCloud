from dataclasses import dataclass, field
from typing import Optional

from google.cloud.bigquery import SchemaField

RAW_DATASET = "crm_data_raw"
CORE_DATASET = "crm_data_core"
MART_DATASET = "crm_data_mart"

RAW_CONTACTS_TABLE = "contacts_raw"
QUARANTINE_TABLE = "contacts_quarantine"
CORE_CONTACTS_TABLE = "core_contacts"

VW_LEAD_ANALYTICS = "vw_lead_analytics"
VW_SALES_FUNNEL = "vw_sales_funnel"
VW_INDUSTRY_ANALYTICS = "vw_industry_analytics"
VW_CONVERSION_METRICS = "vw_conversion_metrics"
VW_DATA_QUALITY = "vw_data_quality"
VW_DAILY_TRENDS = "vw_daily_trends"

CONTACTS_SCHEMA = [
    SchemaField("contact_id", "STRING", mode="REQUIRED"),
    SchemaField("email", "STRING", mode="REQUIRED"),
    SchemaField("first_name", "STRING", mode="NULLABLE"),
    SchemaField("last_name", "STRING", mode="NULLABLE"),
    SchemaField("company_name", "STRING", mode="NULLABLE"),
    SchemaField("job_title", "STRING", mode="NULLABLE"),
    SchemaField("industry", "STRING", mode="NULLABLE"),
    SchemaField("annual_revenue", "INTEGER", mode="NULLABLE"),
    SchemaField("numberofemployees", "INTEGER", mode="NULLABLE"),
    SchemaField("created_at", "TIMESTAMP", mode="NULLABLE"),
    SchemaField("lastmodifieddate", "TIMESTAMP", mode="NULLABLE"),
    SchemaField("lead_status", "STRING", mode="NULLABLE"),
    SchemaField("hs_analytics_source", "STRING", mode="NULLABLE"),
    SchemaField("hs_analytics_source_data_1", "STRING", mode="NULLABLE"),
    SchemaField("processed_at", "TIMESTAMP", mode="REQUIRED"),
    SchemaField("run_id", "STRING", mode="REQUIRED"),
]

QUARANTINE_SCHEMA = [
    SchemaField("id", "STRING", mode="REQUIRED"),
    SchemaField("original_data", "STRING", mode="REQUIRED"),
    SchemaField("error_message", "STRING", mode="REQUIRED"),
    SchemaField("error_type", "STRING", mode="REQUIRED"),
    SchemaField("run_id", "STRING", mode="REQUIRED"),
    SchemaField("quarantined_at", "TIMESTAMP", mode="REQUIRED"),
]

CONTACTS_CLUSTERING_FIELDS = ["lead_status", "industry"]


@dataclass
class TableConfig:
    dataset_id: str
    table_id: str
    schema_fields: list[SchemaField]
    partition_field: Optional[str] = None
    partition_type: str = "DAY"
    clustering_fields: Optional[list[str]] = None
    description: str = ""


TABLE_DEFINITIONS: dict[str, TableConfig] = {
    RAW_CONTACTS_TABLE: TableConfig(
        dataset_id=RAW_DATASET,
        table_id=RAW_CONTACTS_TABLE,
        schema_fields=CONTACTS_SCHEMA,
        partition_field=None,
        clustering_fields=None,
        description="Raw contacts from HubSpot, append-only ingestion layer",
    ),
    QUARANTINE_TABLE: TableConfig(
        dataset_id=RAW_DATASET,
        table_id=QUARANTINE_TABLE,
        schema_fields=QUARANTINE_SCHEMA,
        partition_field=None,
        clustering_fields=None,
        description="Invalid/quarantined contacts with validation error metadata",
    ),
    CORE_CONTACTS_TABLE: TableConfig(
        dataset_id=CORE_DATASET,
        table_id=CORE_CONTACTS_TABLE,
        schema_fields=CONTACTS_SCHEMA,
        partition_field="created_at",
        partition_type="DAY",
        clustering_fields=CONTACTS_CLUSTERING_FIELDS,
        description="Deduplicated, cleaned contacts — single source of truth",
    ),
}
