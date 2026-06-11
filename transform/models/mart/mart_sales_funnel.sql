{{ config(
    alias='mart_sales_funnel',
    description='Sales funnel by lead status with pipeline value'
) }}

SELECT
    COALESCE(lead_status, 'unassigned') AS stage,
    COUNT(*) AS contacts_count,
    ROUND(COUNT(*) / NULLIF(SUM(COUNT(*)) OVER(), 0) * 100, 2) AS percentage_of_total,
    COUNT(DISTINCT company_name) AS unique_companies,
    SUM(annual_revenue) AS pipeline_value,
    CURRENT_TIMESTAMP() AS refreshed_at
FROM {{ ref('core_contacts') }}
GROUP BY lead_status
ORDER BY
    CASE lead_status
        WHEN 'NEW' THEN 1
        WHEN 'OPEN' THEN 2
        WHEN 'IN_PROGRESS' THEN 3
        WHEN 'UNQUALIFIED' THEN 4
        WHEN 'ATTENDED' THEN 5
        WHEN 'CONNECTED' THEN 6
        WHEN 'WORKING' THEN 7
        WHEN 'CLOSED' THEN 8
        ELSE 9
    END
