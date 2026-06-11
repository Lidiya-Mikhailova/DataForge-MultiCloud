{{ config(
    alias='core_contacts',
    materialized='incremental',
    incremental_strategy='merge',
    unique_key='contact_id',
    partition_by={'field': 'created_at', 'data_type': 'timestamp', 'granularity': 'day'},
    cluster_by=['lead_status', 'industry'],
    description='Single source of truth for contacts. Deduplicated via ROW_NUMBER + MERGE upsert.'
) }}

WITH source AS (
    SELECT *
    FROM {{ ref('stg_contacts') }}
    {% if is_incremental() %}
    WHERE processed_at > (
        SELECT COALESCE(MAX(processed_at), TIMESTAMP('1970-01-01'))
        FROM {{ this }}
    )
    {% endif %}
),

deduped AS (
    SELECT
        contact_id,
        email,
        first_name,
        last_name,
        company_name,
        job_title,
        industry,
        annual_revenue,
        numberofemployees,
        created_at,
        lastmodifieddate,
        lead_status,
        hs_analytics_source,
        hs_analytics_source_data_1,
        processed_at,
        run_id
    FROM (
        SELECT *,
            ROW_NUMBER() OVER (
                PARTITION BY contact_id
                ORDER BY lastmodifieddate DESC NULLS LAST,
                         processed_at DESC
            ) AS _rank
        FROM source
    )
    WHERE _rank = 1
)

SELECT * FROM deduped
