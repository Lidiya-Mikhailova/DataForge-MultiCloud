{{ config(
    alias='mart_daily_trends',
    description='Daily new lead trends with conversion and company counts'
) }}

SELECT
    DATE(created_at) AS date,
    COUNT(*) AS new_leads,
    COUNTIF(lead_status = 'CLOSED') AS conversions,
    COUNT(DISTINCT company_name) AS new_companies,
    CURRENT_TIMESTAMP() AS refreshed_at
FROM {{ ref('core_contacts') }}
WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY DATE(created_at)
ORDER BY date DESC
