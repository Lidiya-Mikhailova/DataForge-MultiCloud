{{ config(
    alias='stg_contacts',
    description='Cleaned and type-cast contacts from raw ingestion layer'
) }}

WITH source AS (
    SELECT *
    FROM {{ source('hubspot_raw', 'contacts_raw') }}
    {% if is_incremental() %}
    WHERE processed_at > (
        SELECT COALESCE(MAX(processed_at), TIMESTAMP('1970-01-01'))
        FROM {{ this }}
    )
    {% endif %}
)

SELECT
    contact_id,
    email,
    COALESCE(NULLIF(TRIM(first_name), ''), NULL)   AS first_name,
    COALESCE(NULLIF(TRIM(last_name), ''), NULL)    AS last_name,
    COALESCE(NULLIF(TRIM(company_name), ''), NULL) AS company_name,
    COALESCE(NULLIF(TRIM(job_title), ''), NULL)    AS job_title,
    COALESCE(NULLIF(TRIM(industry), ''), NULL)     AS industry,
    annual_revenue,
    numberofemployees,
    CAST(created_at AS TIMESTAMP)                  AS created_at,
    CAST(lastmodifieddate AS TIMESTAMP)            AS lastmodifieddate,
    COALESCE(NULLIF(TRIM(lead_status), ''), 'UNASSIGNED') AS lead_status,
    COALESCE(NULLIF(TRIM(hs_analytics_source), ''), 'unknown') AS hs_analytics_source,
    hs_analytics_source_data_1,
    CAST(processed_at AS TIMESTAMP)                AS processed_at,
    run_id
FROM source
WHERE contact_id IS NOT NULL
  AND email IS NOT NULL
  AND email != ''
