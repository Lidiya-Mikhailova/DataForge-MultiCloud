-- ============================================================================
-- DDL: BigQuery CORE Dataset
-- Purpose: Deduplicated, cleaned, partitioned warehouse tables
-- Dataset: crm_data_core
-- ============================================================================

-- Core Contacts (single source of truth, partitioned + clustered)
CREATE TABLE IF NOT EXISTS crm_data_core.core_contacts (
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
PARTITION BY DATE(created_at)
CLUSTER BY lead_status, industry
OPTIONS (
    description = "Deduplicated, cleaned contacts — single source of truth for analytics"
);
