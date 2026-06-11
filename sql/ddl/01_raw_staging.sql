-- ============================================================================
-- DDL: BigQuery RAW / STAGING Dataset
-- Purpose: Append-only landing zone for validated data
-- Dataset: crm_data_raw
-- ============================================================================

-- RAW Contacts (append-only, ingestion-time partitioned)
CREATE TABLE IF NOT EXISTS crm_data_raw.contacts_raw (
    contact_id          STRING  NOT NULL,
    email               STRING  NOT NULL,
    first_name          STRING,
    last_name           STRING,
    company_name        STRING,
    job_title           STRING,
    industry            STRING,
    annual_revenue      INTEGER,
    numberofemployees   INTEGER,
    created_at          TIMESTAMP,
    lastmodifieddate    TIMESTAMP,
    lead_status         STRING,
    hs_analytics_source STRING,
    hs_analytics_source_data_1 STRING,
    processed_at        TIMESTAMP NOT NULL,
    run_id              STRING  NOT NULL
)
PARTITION BY DATE(_PARTITIONTIME)
OPTIONS (
    description = "Raw contacts from HubSpot, append-only ingestion layer"
);

-- Contacts Quarantine (invalid records with validation metadata)
CREATE TABLE IF NOT EXISTS crm_data_raw.contacts_quarantine (
    id              STRING  NOT NULL,
    original_data   JSON    NOT NULL,
    error_message   STRING  NOT NULL,
    error_type      STRING  NOT NULL,
    run_id          STRING  NOT NULL,
    quarantined_at  TIMESTAMP NOT NULL
)
PARTITION BY DATE(_PARTITIONTIME)
OPTIONS (
    description = "Invalid/quarantined contacts with validation error metadata"
);
