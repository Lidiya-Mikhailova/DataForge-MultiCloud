{{ config(
    alias='mart_conversion_metrics',
    description='Conversion metrics across 7-day, 30-day, and all-time windows'
) }}

SELECT * FROM (
    SELECT 'Last 7 days' AS period,
        COUNT(*) AS total_leads,
        COUNTIF(lead_status = 'CLOSED') AS converted,
        ROUND(COUNTIF(lead_status = 'CLOSED') / NULLIF(COUNT(*), 0) * 100, 2) AS conversion_rate,
        AVG(IF(lead_status = 'CLOSED', annual_revenue, NULL)) AS avg_deal_size,
        CURRENT_TIMESTAMP() AS refreshed_at
    FROM {{ ref('core_contacts') }}
    WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
)
UNION ALL
SELECT * FROM (
    SELECT 'Last 30 days' AS period,
        COUNT(*) AS total_leads,
        COUNTIF(lead_status = 'CLOSED') AS converted,
        ROUND(COUNTIF(lead_status = 'CLOSED') / NULLIF(COUNT(*), 0) * 100, 2) AS conversion_rate,
        AVG(IF(lead_status = 'CLOSED', annual_revenue, NULL)) AS avg_deal_size,
        CURRENT_TIMESTAMP() AS refreshed_at
    FROM {{ ref('core_contacts') }}
    WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
)
UNION ALL
SELECT * FROM (
    SELECT 'All time' AS period,
        COUNT(*) AS total_leads,
        COUNTIF(lead_status = 'CLOSED') AS converted,
        ROUND(COUNTIF(lead_status = 'CLOSED') / NULLIF(COUNT(*), 0) * 100, 2) AS conversion_rate,
        AVG(IF(lead_status = 'CLOSED', annual_revenue, NULL)) AS avg_deal_size,
        CURRENT_TIMESTAMP() AS refreshed_at
    FROM {{ ref('core_contacts') }}
)
