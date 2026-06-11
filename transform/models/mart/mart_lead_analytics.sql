{{ config(
    alias='mart_lead_analytics',
    description='Lead source analytics — conversion rates and revenue by acquisition channel'
) }}

SELECT
    COALESCE(hs_analytics_source, 'unknown') AS lead_source,
    COUNT(*) AS total_leads,
    COUNT(DISTINCT contact_id) AS unique_contacts,
    COUNTIF(lead_status = 'CLOSED') AS converted_leads,
    ROUND(COUNTIF(lead_status = 'CLOSED') / NULLIF(COUNT(*), 0) * 100, 2) AS conversion_rate_pct,
    ROUND(AVG(annual_revenue), 2) AS avg_annual_revenue,
    SUM(annual_revenue) AS total_revenue,
    CURRENT_TIMESTAMP() AS refreshed_at
FROM {{ ref('core_contacts') }}
WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
GROUP BY lead_source
ORDER BY total_leads DESC
