{{ config(
    alias='mart_data_quality',
    description='Data quality dashboard — valid vs invalid record counts and quality score'
) }}

WITH stats AS (
    SELECT
        (SELECT COUNT(*) FROM {{ ref('core_contacts') }}) AS valid_count,
        (SELECT COUNT(*) FROM {{ source('hubspot_raw', 'contacts_quarantine') }}) AS invalid_count
)

SELECT 'Total Records' AS metric, CAST(valid_count + invalid_count AS STRING) AS value
FROM stats
UNION ALL
SELECT 'Valid Records', CAST(valid_count AS STRING)
FROM stats
UNION ALL
SELECT 'Invalid Records', CAST(invalid_count AS STRING)
FROM stats
UNION ALL
SELECT 'Data Quality Score %',
    CAST(ROUND(valid_count / NULLIF(valid_count + invalid_count, 0) * 100, 2) AS STRING)
FROM stats
