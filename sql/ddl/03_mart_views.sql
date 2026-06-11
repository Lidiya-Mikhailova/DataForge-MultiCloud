-- ============================================================================
-- DDL: BigQuery MART Views
-- Purpose: BI-ready analytical views for dashboards and reporting
-- Dataset: crm_data_mart
-- ============================================================================

-- Lead Source Analytics
CREATE OR REPLACE VIEW crm_data_mart.vw_lead_analytics AS
SELECT
    COALESCE(hs_analytics_source, 'unknown') AS lead_source,
    COUNT(*) AS total_leads,
    COUNT(DISTINCT contact_id) AS unique_contacts,
    COUNTIF(lead_status = 'CLOSED') AS converted_leads,
    ROUND(COUNTIF(lead_status = 'CLOSED') / NULLIF(COUNT(*), 0) * 100, 2) AS conversion_rate_pct,
    ROUND(AVG(annual_revenue), 2) AS avg_annual_revenue,
    SUM(annual_revenue) AS total_revenue
FROM `crm_data_core.core_contacts`
WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
GROUP BY lead_source;

-- Sales Funnel
CREATE OR REPLACE VIEW crm_data_mart.vw_sales_funnel AS
SELECT
    COALESCE(lead_status, 'unassigned') AS stage,
    COUNT(*) AS contacts_count,
    ROUND(COUNT(*) / NULLIF(SUM(COUNT(*)) OVER(), 0) * 100, 2) AS percentage_of_total,
    COUNT(DISTINCT company_name) AS unique_companies,
    SUM(annual_revenue) AS pipeline_value
FROM `crm_data_core.core_contacts`
GROUP BY lead_status;

-- Industry Analytics
CREATE OR REPLACE VIEW crm_data_mart.vw_industry_analytics AS
SELECT
    COALESCE(industry, 'unknown') AS industry,
    COUNT(*) AS total_leads,
    COUNT(DISTINCT contact_id) AS unique_contacts,
    COUNT(DISTINCT company_name) AS companies,
    COUNTIF(lead_status = 'CLOSED') AS customers,
    ROUND(COUNTIF(lead_status = 'CLOSED') / NULLIF(COUNT(*), 0) * 100, 2) AS conversion_rate,
    ROUND(AVG(annual_revenue), 2) AS avg_revenue,
    SUM(annual_revenue) AS total_revenue
FROM `crm_data_core.core_contacts`
GROUP BY industry;

-- Conversion Metrics (multi-period)
CREATE OR REPLACE VIEW crm_data_mart.vw_conversion_metrics AS
SELECT * FROM (
    SELECT 'Last 7 days' AS period,
        COUNT(*) AS total_leads,
        COUNTIF(lead_status = 'CLOSED') AS converted,
        ROUND(COUNTIF(lead_status = 'CLOSED') / NULLIF(COUNT(*), 0) * 100, 2) AS conversion_rate,
        AVG(IF(lead_status = 'CLOSED', annual_revenue, NULL)) AS avg_deal_size
    FROM `crm_data_core.core_contacts`
    WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
)
UNION ALL
SELECT * FROM (
    SELECT 'Last 30 days' AS period,
        COUNT(*) AS total_leads,
        COUNTIF(lead_status = 'CLOSED') AS converted,
        ROUND(COUNTIF(lead_status = 'CLOSED') / NULLIF(COUNT(*), 0) * 100, 2) AS conversion_rate,
        AVG(IF(lead_status = 'CLOSED', annual_revenue, NULL)) AS avg_deal_size
    FROM `crm_data_core.core_contacts`
    WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
)
UNION ALL
SELECT * FROM (
    SELECT 'All time' AS period,
        COUNT(*) AS total_leads,
        COUNTIF(lead_status = 'CLOSED') AS converted,
        ROUND(COUNTIF(lead_status = 'CLOSED') / NULLIF(COUNT(*), 0) * 100, 2) AS conversion_rate,
        AVG(IF(lead_status = 'CLOSED', annual_revenue, NULL)) AS avg_deal_size
    FROM `crm_data_core.core_contacts`
);

-- Data Quality Metrics
CREATE OR REPLACE VIEW crm_data_mart.vw_data_quality AS
WITH stats AS (
    SELECT
        (SELECT COUNT(*) FROM `crm_data_core.core_contacts`) AS valid_count,
        (SELECT COUNT(*) FROM `crm_data_raw.contacts_quarantine`) AS invalid_count
)
SELECT 'Total Records' AS metric, CAST(valid_count + invalid_count AS STRING) AS value FROM stats
UNION ALL
SELECT 'Valid Records', CAST(valid_count AS STRING) FROM stats
UNION ALL
SELECT 'Invalid Records', CAST(invalid_count AS STRING) FROM stats
UNION ALL
SELECT 'Data Quality Score %',
    CAST(ROUND(valid_count / NULLIF(valid_count + invalid_count, 0) * 100, 2) AS STRING)
FROM stats;

-- Daily New Lead Trends
CREATE OR REPLACE VIEW crm_data_mart.vw_daily_trends AS
SELECT
    DATE(created_at) AS date,
    COUNT(*) AS new_leads,
    COUNTIF(lead_status = 'CLOSED') AS conversions,
    COUNT(DISTINCT company_name) AS new_companies
FROM `crm_data_core.core_contacts`
WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY DATE(created_at);
