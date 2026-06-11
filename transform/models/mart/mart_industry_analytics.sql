{{ config(
    alias='mart_industry_analytics',
    description='Industry breakdown — conversion rates, revenue, and company distribution'
) }}

SELECT
    COALESCE(industry, 'unknown') AS industry,
    COUNT(*) AS total_leads,
    COUNT(DISTINCT contact_id) AS unique_contacts,
    COUNT(DISTINCT company_name) AS companies,
    COUNTIF(lead_status = 'CLOSED') AS customers,
    ROUND(COUNTIF(lead_status = 'CLOSED') / NULLIF(COUNT(*), 0) * 100, 2) AS conversion_rate,
    ROUND(AVG(annual_revenue), 2) AS avg_revenue,
    SUM(annual_revenue) AS total_revenue,
    CURRENT_TIMESTAMP() AS refreshed_at
FROM {{ ref('core_contacts') }}
GROUP BY industry
ORDER BY total_leads DESC
