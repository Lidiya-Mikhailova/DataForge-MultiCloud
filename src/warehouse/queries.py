MART_DATASET = "crm_data_mart"
VW_LEAD_ANALYTICS = "vw_lead_analytics"
VW_SALES_FUNNEL = "vw_sales_funnel"
VW_INDUSTRY_ANALYTICS = "vw_industry_analytics"
VW_CONVERSION_METRICS = "vw_conversion_metrics"
VW_DATA_QUALITY = "vw_data_quality"
VW_DAILY_TRENDS = "vw_daily_trends"


def build_merge_core_query(
    project_id: str,
    raw_dataset: str,
    raw_table: str,
    core_dataset: str,
    core_table: str,
) -> str:
    return f"""
    MERGE `{project_id}.{core_dataset}.{core_table}` T
    USING (
        SELECT * EXCEPT(_rank) FROM (
            SELECT *,
                ROW_NUMBER() OVER (
                    PARTITION BY contact_id
                    ORDER BY lastmodifieddate DESC, processed_at DESC
                ) AS _rank
            FROM `{project_id}.{raw_dataset}.{raw_table}`
            WHERE run_id = @run_id
        )
        WHERE _rank = 1
    ) S
    ON T.contact_id = S.contact_id
    WHEN MATCHED THEN
        UPDATE SET
            email = S.email,
            first_name = S.first_name,
            last_name = S.last_name,
            company_name = S.company_name,
            job_title = S.job_title,
            industry = S.industry,
            annual_revenue = S.annual_revenue,
            numberofemployees = S.numberofemployees,
            created_at = S.created_at,
            lastmodifieddate = S.lastmodifieddate,
            lead_status = S.lead_status,
            hs_analytics_source = S.hs_analytics_source,
            hs_analytics_source_data_1 = S.hs_analytics_source_data_1,
            processed_at = CURRENT_TIMESTAMP(),
            run_id = S.run_id
    WHEN NOT MATCHED THEN
        INSERT (
            contact_id, email, first_name, last_name, company_name,
            job_title, industry, annual_revenue, numberofemployees,
            created_at, lastmodifieddate, lead_status,
            hs_analytics_source, hs_analytics_source_data_1,
            processed_at, run_id
        )
        VALUES (
            S.contact_id, S.email, S.first_name, S.last_name, S.company_name,
            S.job_title, S.industry, S.annual_revenue, S.numberofemployees,
            S.created_at, S.lastmodifieddate, S.lead_status,
            S.hs_analytics_source, S.hs_analytics_source_data_1,
            CURRENT_TIMESTAMP(), S.run_id
        )
    """


def build_view_lead_analytics(project_id: str, core_dataset: str, core_table: str) -> str:
    return f"""
    CREATE OR REPLACE VIEW `{project_id}.{MART_DATASET}.{VW_LEAD_ANALYTICS}` AS
    SELECT
        COALESCE(hs_analytics_source, 'unknown') AS lead_source,
        COUNT(*) AS total_leads,
        COUNT(DISTINCT contact_id) AS unique_contacts,
        COUNTIF(lead_status = 'CLOSED') AS converted_leads,
        ROUND(COUNTIF(lead_status = 'CLOSED') / NULLIF(COUNT(*), 0) * 100, 2) AS conversion_rate_pct,
        ROUND(AVG(annual_revenue), 2) AS avg_annual_revenue,
        SUM(annual_revenue) AS total_revenue
    FROM `{project_id}.{core_dataset}.{core_table}`
    WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
    GROUP BY lead_source
    """


def build_view_sales_funnel(project_id: str, core_dataset: str, core_table: str) -> str:
    return f"""
    CREATE OR REPLACE VIEW `{project_id}.{MART_DATASET}.{VW_SALES_FUNNEL}` AS
    SELECT
        COALESCE(lead_status, 'unassigned') AS stage,
        COUNT(*) AS contacts_count,
        ROUND(COUNT(*) / NULLIF(SUM(COUNT(*)) OVER(), 0) * 100, 2) AS percentage_of_total,
        COUNT(DISTINCT company_name) AS unique_companies,
        SUM(annual_revenue) AS pipeline_value
    FROM `{project_id}.{core_dataset}.{core_table}`
    GROUP BY lead_status
    """


def build_view_industry_analytics(project_id: str, core_dataset: str, core_table: str) -> str:
    return f"""
    CREATE OR REPLACE VIEW `{project_id}.{MART_DATASET}.{VW_INDUSTRY_ANALYTICS}` AS
    SELECT
        COALESCE(industry, 'unknown') AS industry,
        COUNT(*) AS total_leads,
        COUNT(DISTINCT contact_id) AS unique_contacts,
        COUNT(DISTINCT company_name) AS companies,
        COUNTIF(lead_status = 'CLOSED') AS customers,
        ROUND(COUNTIF(lead_status = 'CLOSED') / NULLIF(COUNT(*), 0) * 100, 2) AS conversion_rate,
        ROUND(AVG(annual_revenue), 2) AS avg_revenue,
        SUM(annual_revenue) AS total_revenue
    FROM `{project_id}.{core_dataset}.{core_table}`
    GROUP BY industry
    """


def build_view_conversion_metrics(project_id: str, core_dataset: str, core_table: str) -> str:
    return f"""
    CREATE OR REPLACE VIEW `{project_id}.{MART_DATASET}.{VW_CONVERSION_METRICS}` AS
    SELECT * FROM (
        SELECT 'Last 7 days' AS period,
            COUNT(*) AS total_leads,
            COUNTIF(lead_status = 'CLOSED') AS converted,
            ROUND(COUNTIF(lead_status = 'CLOSED') / NULLIF(COUNT(*), 0) * 100, 2) AS conversion_rate,
            AVG(IF(lead_status = 'CLOSED', annual_revenue, NULL)) AS avg_deal_size
        FROM `{project_id}.{core_dataset}.{core_table}`
        WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
    )
    UNION ALL
    SELECT * FROM (
        SELECT 'Last 30 days' AS period,
            COUNT(*) AS total_leads,
            COUNTIF(lead_status = 'CLOSED') AS converted,
            ROUND(COUNTIF(lead_status = 'CLOSED') / NULLIF(COUNT(*), 0) * 100, 2) AS conversion_rate,
            AVG(IF(lead_status = 'CLOSED', annual_revenue, NULL)) AS avg_deal_size
        FROM `{project_id}.{core_dataset}.{core_table}`
        WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
    )
    UNION ALL
    SELECT * FROM (
        SELECT 'All time' AS period,
            COUNT(*) AS total_leads,
            COUNTIF(lead_status = 'CLOSED') AS converted,
            ROUND(COUNTIF(lead_status = 'CLOSED') / NULLIF(COUNT(*), 0) * 100, 2) AS conversion_rate,
            AVG(IF(lead_status = 'CLOSED', annual_revenue, NULL)) AS avg_deal_size
        FROM `{project_id}.{core_dataset}.{core_table}`
    )
    """


def build_view_data_quality(project_id: str, raw_dataset: str, quarantine_table: str,
                            core_dataset: str, core_table: str) -> str:
    return f"""
    CREATE OR REPLACE VIEW `{project_id}.{MART_DATASET}.{VW_DATA_QUALITY}` AS
    WITH stats AS (
        SELECT
            (SELECT COUNT(*) FROM `{project_id}.{core_dataset}.{core_table}`) AS valid_count,
            (SELECT COUNT(*) FROM `{project_id}.{raw_dataset}.{quarantine_table}`) AS invalid_count
    )
    SELECT 'Total Records' AS metric, CAST(valid_count + invalid_count AS STRING) AS value FROM stats
    UNION ALL
    SELECT 'Valid Records', CAST(valid_count AS STRING) FROM stats
    UNION ALL
    SELECT 'Invalid Records', CAST(invalid_count AS STRING) FROM stats
    UNION ALL
    SELECT 'Data Quality Score %',
        CAST(ROUND(valid_count / NULLIF(valid_count + invalid_count, 0) * 100, 2) AS STRING)
    FROM stats
    """


def build_view_daily_trends(project_id: str, core_dataset: str, core_table: str) -> str:
    return f"""
    CREATE OR REPLACE VIEW `{project_id}.{MART_DATASET}.{VW_DAILY_TRENDS}` AS
    SELECT
        DATE(created_at) AS date,
        COUNT(*) AS new_leads,
        COUNTIF(lead_status = 'CLOSED') AS conversions,
        COUNT(DISTINCT company_name) AS new_companies
    FROM `{project_id}.{core_dataset}.{core_table}`
    WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
    GROUP BY DATE(created_at)
    """


def build_all_mart_views(project_id: str, core_dataset: str, core_table: str,
                         raw_dataset: str, quarantine_table: str) -> list[tuple[str, str]]:
    return [
        (VW_LEAD_ANALYTICS, build_view_lead_analytics(project_id, core_dataset, core_table)),
        (VW_SALES_FUNNEL, build_view_sales_funnel(project_id, core_dataset, core_table)),
        (VW_INDUSTRY_ANALYTICS, build_view_industry_analytics(project_id, core_dataset, core_table)),
        (VW_CONVERSION_METRICS, build_view_conversion_metrics(project_id, core_dataset, core_table)),
        (VW_DATA_QUALITY, build_view_data_quality(project_id, raw_dataset, quarantine_table, core_dataset, core_table)),
        (VW_DAILY_TRENDS, build_view_daily_trends(project_id, core_dataset, core_table)),
    ]
