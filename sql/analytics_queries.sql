-- ============================================================================
-- BigQuery Analytical Queries for DataForge CRM
-- Dataset: crm_data
-- ============================================================================

-- ============================================================================
-- 1. АНАЛИЗ ЛИДОВ ПО ИСТОЧНИКАМ
-- ============================================================================

-- Статистика лидов по источникам (каналы привлечения)
SELECT
  COALESCE(hs_analytics_source, 'unknown') AS lead_source,
  COUNT(*) AS total_leads,
  COUNT(DISTINCT contact_id) AS unique_contacts,
  COUNTIF(lead_status = 'CLOSED') AS converted_leads,
  ROUND(COUNTIF(lead_status = 'CLOSED') / COUNT(*) * 100, 2) AS conversion_rate_pct,
  ROUND(AVG(annual_revenue), 2) AS avg_annual_revenue,
  SUM(annual_revenue) AS total_revenue
FROM `crm_data.contacts`
WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
GROUP BY lead_source
ORDER BY total_leads DESC;


-- Детальная разбивка по источникам и кампаниям
SELECT
  COALESCE(hs_analytics_source, 'unknown') AS source,
  COALESCE(hs_analytics_source_data_1, 'N/A') AS campaign,
  DATE_TRUNC(created_at, WEEK) AS week_start,
  COUNT(*) AS leads_count,
  COUNTIF(lead_status = 'CLOSED') AS converted_count,
  ROUND(COUNTIF(lead_status = 'CLOSED') / COUNT(*) * 100, 2) AS conversion_rate
FROM `crm_data.contacts`
GROUP BY source, campaign, week_start
ORDER BY week_start DESC, leads_count DESC;


-- Топ источников по конверсии (минимум 10 лидов)
SELECT
  COALESCE(hs_analytics_source, 'unknown') AS lead_source,
  COUNT(*) AS total_leads,
  COUNTIF(lead_status = 'CLOSED') AS converted,
  ROUND(COUNTIF(lead_status = 'CLOSED') / COUNT(*) * 100, 2) AS conversion_rate
FROM `crm_data.contacts`
GROUP BY lead_source
HAVING COUNT(*) >= 10
ORDER BY conversion_rate DESC
LIMIT 10;


-- ============================================================================
-- 2. АНАЛИЗ ВОРОНКИ ПРОДАЖ
-- ============================================================================

-- Общая воронка продаж по статусам
SELECT
  COALESCE(lead_status, 'unassigned') AS stage,
  COUNT(*) AS contacts_count,
  ROUND(COUNT(*) / SUM(COUNT(*)) OVER() * 100, 2) AS percentage_of_total,
  COUNT(DISTINCT company_name) AS unique_companies,
  SUM(annual_revenue) AS pipeline_value
FROM `crm_data.contacts`
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
  END;


-- Воронка с конверсией между стадиями
WITH funnel AS (
  SELECT
    CASE
      WHEN lead_status IN ('NEW', 'OPEN') THEN '1_leads'
      WHEN lead_status = 'IN_PROGRESS' THEN '2_qualified'
      WHEN lead_status IN ('ATTENDED', 'CONNECTED') THEN '3_engaged'
      WHEN lead_status = 'WORKING' THEN '4_working'
      WHEN lead_status = 'CLOSED' THEN '5_converted'
      ELSE '0_unassigned'
    END AS stage_bucket
  FROM `crm_data.contacts`
  WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
)
SELECT
  stage_bucket,
  COUNT(*) AS count,
  LAG(COUNT(*)) OVER (ORDER BY stage_bucket) AS previous_stage_count,
  ROUND(COUNT(*) / LAG(COUNT(*)) OVER (ORDER BY stage_bucket) * 100, 2) AS stage_conversion_rate
FROM funnel
GROUP BY stage_bucket
ORDER BY stage_bucket;


-- Тренд воронки по неделям
SELECT
  DATE_TRUNC(created_at, WEEK) AS week_start,
  COUNTIF(lead_status IN ('NEW', 'OPEN')) AS new_leads,
  COUNTIF(lead_status = 'IN_PROGRESS') AS qualified,
  COUNTIF(lead_status IN ('ATTENDED', 'CONNECTED')) AS engaged,
  COUNTIF(lead_status = 'WORKING') AS working,
  COUNTIF(lead_status = 'CLOSED') AS converted
FROM `crm_data.contacts`
WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
GROUP BY week_start
ORDER BY week_start;


-- ============================================================================
-- 3. РАСЧЕТ КОНВЕРСИИ В КЛИЕНТОВ
-- ============================================================================

-- Общая конверсия с разбивкой по периодам
SELECT
  'Last 7 days' AS period,
  COUNT(*) AS total_leads,
  COUNTIF(lead_status = 'CLOSED') AS converted,
  ROUND(COUNTIF(lead_status = 'CLOSED') / COUNT(*) * 100, 2) AS conversion_rate,
  AVG(IF(lead_status = 'CLOSED', annual_revenue, NULL)) AS avg_deal_size
FROM `crm_data.contacts`
WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)

UNION ALL

SELECT
  'Last 30 days' AS period,
  COUNT(*) AS total_leads,
  COUNTIF(lead_status = 'CLOSED') AS converted,
  ROUND(COUNTIF(lead_status = 'CLOSED') / COUNT(*) * 100, 2) AS conversion_rate,
  AVG(IF(lead_status = 'CLOSED', annual_revenue, NULL)) AS avg_deal_size
FROM `crm_data.contacts`
WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)

UNION ALL

SELECT
  'Last 90 days' AS period,
  COUNT(*) AS total_leads,
  COUNTIF(lead_status = 'CLOSED') AS converted,
  ROUND(COUNTIF(lead_status = 'CLOSED') / COUNT(*) * 100, 2) AS conversion_rate,
  AVG(IF(lead_status = 'CLOSED', annual_revenue, NULL)) AS avg_deal_size
FROM `crm_data.contacts`
WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)

UNION ALL

SELECT
  'All time' AS period,
  COUNT(*) AS total_leads,
  COUNTIF(lead_status = 'CLOSED') AS converted,
  ROUND(COUNTIF(lead_status = 'CLOSED') / COUNT(*) * 100, 2) AS conversion_rate,
  AVG(IF(lead_status = 'CLOSED', annual_revenue, NULL)) AS avg_deal_size
FROM `crm_data.contacts`;


-- Конверсия по источникам с временным лагом (time to conversion)
SELECT
  COALESCE(hs_analytics_source, 'unknown') AS source,
  COUNT(*) AS total_leads,
  COUNTIF(lead_status = 'CLOSED') AS converted,
  ROUND(COUNTIF(lead_status = 'CLOSED') / COUNT(*) * 100, 2) AS conversion_rate,
  ROUND(AVG(
    IF(lead_status = 'CLOSED',
      DATE_DIFF(CAST(lastmodifieddate AS DATE), CAST(created_at AS DATE), DAY),
      NULL)
  ), 1) AS avg_days_to_convert
FROM `crm_data.contacts`
WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 180 DAY)
GROUP BY source
ORDER BY conversion_rate DESC;


-- Воронка конверсии с бюджетом (если есть данные о затратах)
SELECT
  DATE_TRUNC(created_at, MONTH) AS month,
  COUNT(*) AS leads_generated,
  COUNTIF(lead_status = 'CLOSED') AS customers_acquired,
  ROUND(COUNTIF(lead_status = 'CLOSED') / COUNT(*) * 100, 2) AS conversion_rate,
  SUM(annual_revenue) AS total_revenue,
  SUM(annual_revenue) / COUNT(*) AS revenue_per_lead
FROM `crm_data.contacts`
GROUP BY month
ORDER BY month DESC;


-- ============================================================================
-- 4. ДИНАМИКА НОВЫХ ПОЛЬЗОВАТЕЛЕЙ ПО ДНЯМ
-- ============================================================================

-- Ежедневная динамика новых лидов
SELECT
  DATE(created_at) AS date,
  COUNT(*) AS new_leads,
  COUNTIF(lead_status = 'CLOSED') AS conversions,
  ROUND(COUNTIF(lead_status = 'CLOSED') / COUNT(*) * 100, 2) AS conversion_rate,
  COUNT(DISTINCT company_name) AS new_companies
FROM `crm_data.contacts`
WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY DATE(created_at)
ORDER BY date DESC;


-- Недельная динамика с трендом
SELECT
  DATE_TRUNC(created_at, WEEK) AS week_start,
  COUNT(*) AS weekly_leads,
  LAG(COUNT(*)) OVER (ORDER BY DATE_TRUNC(created_at, WEEK)) AS previous_week,
  ROUND((COUNT(*) - LAG(COUNT(*)) OVER (ORDER BY DATE_TRUNC(created_at, WEEK))) /
    LAG(COUNT(*)) OVER (ORDER BY DATE_TRUNC(created_at, WEEK)) * 100, 2) AS week_over_week_change_pct,
  COUNTIF(lead_status = 'CLOSED') AS weekly_conversions
FROM `crm_data.contacts`
WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
GROUP BY week_start
ORDER BY week_start DESC;


-- Месячная динамика с скользящим средним
SELECT
  DATE_TRUNC(created_at, MONTH) AS month,
  COUNT(*) AS monthly_leads,
  AVG(COUNT(*)) OVER (
    ORDER BY DATE_TRUNC(created_at, MONTH)
    ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
  ) AS rolling_3month_avg,
  COUNTIF(lead_status = 'CLOSED') AS monthly_conversions,
  ROUND(COUNTIF(lead_status = 'CLOSED') / COUNT(*) * 100, 2) AS monthly_conversion_rate
FROM `crm_data.contacts`
GROUP BY month
ORDER BY month DESC;


-- Сравнение периодов (текущий vs предыдущий)
SELECT
  'Current Period' AS period,
  COUNT(*) AS leads,
  COUNTIF(lead_status = 'CLOSED') AS conversions,
  ROUND(COUNTIF(lead_status = 'CLOSED') / COUNT(*) * 100, 2) AS conversion_rate
FROM `crm_data.contacts`
WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)

UNION ALL

SELECT
  'Previous Period' AS period,
  COUNT(*) AS leads,
  COUNTIF(lead_status = 'CLOSED') AS conversions,
  ROUND(COUNTIF(lead_status = 'CLOSED') / COUNT(*) * 100, 2) AS conversion_rate
FROM `crm_data.contacts`
WHERE created_at BETWEEN TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 60 DAY)
  AND TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY);


-- ============================================================================
-- 5. РАСПРЕДЕЛЕНИЕ ПО ИНДУСТРИЯМ
-- ============================================================================

-- Топ индустрий по количеству лидов
SELECT
  COALESCE(industry, 'unknown') AS industry,
  COUNT(*) AS total_leads,
  COUNT(DISTINCT contact_id) AS unique_contacts,
  COUNT(DISTINCT company_name) AS companies,
  COUNTIF(lead_status = 'CLOSED') AS customers,
  ROUND(COUNTIF(lead_status = 'CLOSED') / COUNT(*) * 100, 2) AS conversion_rate,
  ROUND(AVG(annual_revenue), 2) AS avg_revenue,
  SUM(annual_revenue) AS total_revenue
FROM `crm_data.contacts`
GROUP BY industry
ORDER BY total_leads DESC;


-- Разбивка индустрий по статусам (тепловая карта)
SELECT
  COALESCE(industry, 'unknown') AS industry,
  COUNTIF(lead_status = 'NEW' OR lead_status = 'OPEN') AS new_leads,
  COUNTIF(lead_status = 'IN_PROGRESS') AS qualified,
  COUNTIF(lead_status IN ('ATTENDED', 'CONNECTED')) AS engaged,
  COUNTIF(lead_status = 'WORKING') AS working,
  COUNTIF(lead_status = 'CLOSED') AS converted,
  COUNTIF(lead_status = 'UNQUALIFIED') AS disqualified,
  COUNT(*) AS total
FROM `crm_data.contacts`
GROUP BY industry
ORDER BY total DESC;


-- Индустрии по среднему чеку
SELECT
  COALESCE(industry, 'unknown') AS industry,
  COUNT(*) AS deals_count,
  ROUND(AVG(annual_revenue), 2) AS avg_deal_size,
  PERCENTILE_CONT(annual_revenue, 0.5) OVER (PARTITION BY industry) AS median_deal_size,
  MIN(annual_revenue) AS min_deal,
  MAX(annual_revenue) AS max_deal,
  SUM(annual_revenue) AS total_revenue
FROM `crm_data.contacts`
WHERE annual_revenue > 0
GROUP BY industry
ORDER BY avg_deal_size DESC;


-- Размер компаний в индустриях
SELECT
  COALESCE(industry, 'unknown') AS industry,
  COUNTIF(numberofemployees < 50) AS small_companies,
  COUNTIF(numberofemployees BETWEEN 50 AND 250) AS mid_companies,
  COUNTIF(numberofemployees > 250) AS large_companies,
  ROUND(AVG(numberofemployees), 0) AS avg_employees
FROM `crm_data.contacts`
GROUP BY industry
ORDER BY (COUNTIF(numberofemployees < 50) + COUNTIF(numberofemployees BETWEEN 50 AND 250) +
  COUNTIF(numberofemployees > 250)) DESC;


-- ============================================================================
-- 6. АНАЛИЗ НЕВАЛИДНЫХ ДАННЫХ (invalid_contacts)
-- ============================================================================

-- Общая статистика качества данных
SELECT
  'Total Records' AS metric,
  (SELECT COUNT(*) FROM `crm_data.contacts`) AS value
UNION ALL
SELECT
  'Valid Records' AS metric,
  (SELECT COUNT(*) FROM `crm_data.contacts`) -
  (SELECT COUNT(*) FROM `crm_data.invalid_contacts`) AS value
UNION ALL
SELECT
  'Invalid Records' AS metric,
  (SELECT COUNT(*) FROM `crm_data.invalid_contacts`) AS value
UNION ALL
SELECT
  'Data Quality Score %' AS metric,
  ROUND(
    ((SELECT COUNT(*) FROM `crm_data.contacts`) -
     (SELECT COUNT(*) FROM `crm_data.invalid_contacts`)) /
    (SELECT COUNT(*) FROM `crm_data.contacts`) * 100,
  2) AS value;


-- Подсчет ошибок по типам
SELECT
  error_type,
  COUNT(*) AS error_count,
  ROUND(COUNT(*) / SUM(COUNT(*)) OVER() * 100, 2) AS percentage,
  COUNT(DISTINCT SAFE_CAST(JSON_VALUE(original_data, '$.contact_id') AS STRING)) AS affected_records
FROM `crm_data.invalid_contacts`
GROUP BY error_type
ORDER BY error_count DESC;


-- Детальная статистика по типам ошибок
SELECT
  error_type,
  COUNT(*) AS total_errors,
  COUNT(DISTINCT JSON_VALUE(original_data, '$.email')) AS unique_emails_affected,
  MIN(CAST(JSON_VALUE(original_data, '$.created_at') AS TIMESTAMP)) AS earliest_error,
  MAX(CAST(JSON_VALUE(original_data, '$.created_at') AS TIMESTAMP)) AS latest_error
FROM `crm_data.invalid_contacts`
GROUP BY error_type
ORDER BY total_errors DESC;


-- Распределение ошибок по датам
SELECT
  DATE(processed_at) AS error_date,
  COUNT(*) AS daily_errors,
  COUNT(DISTINCT error_type) AS unique_error_types,
  COUNTIF(error_type = 'validation_error') AS validation_errors,
  COUNTIF(error_type = 'missing_field') AS missing_field_errors,
  COUNTIF(error_type = 'invalid_format') AS format_errors
FROM `crm_data.invalid_contacts`
WHERE processed_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY DATE(processed_at)
ORDER BY error_date DESC;


-- Топ ошибок по email (проблемные контакты)
SELECT
  JSON_VALUE(original_data, '$.email') AS email,
  JSON_VALUE(original_data, '$.company_name') AS company,
  COUNT(*) AS error_count,
  STRING_AGG(DISTINCT error_type, ', ') AS error_types,
  STRING_AGG(DISTINCT error_message, '; ') AS error_messages
FROM `crm_data.invalid_contacts`
GROUP BY
  JSON_VALUE(original_data, '$.email'),
  JSON_VALUE(original_data, '$.company_name')
HAVING COUNT(*) > 1
ORDER BY error_count DESC
LIMIT 20;


-- Эффективность валидации по полям
SELECT
  'email' AS field_name,
  COUNTIF(JSON_VALUE(original_data, '$.email') IS NULL OR
          JSON_VALUE(original_data, '$.email') = '') AS null_or_empty,
  (SELECT COUNT(*) FROM `crm_data.invalid_contacts`) AS total_invalid
FROM `crm_data.invalid_contacts`

UNION ALL

SELECT
  'company_name' AS field_name,
  COUNTIF(JSON_VALUE(original_data, '$.company_name') IS NULL OR
          JSON_VALUE(original_data, '$.company_name') = '') AS null_or_empty,
  (SELECT COUNT(*) FROM `crm_data.invalid_contacts`)
FROM `crm_data.invalid_contacts`

UNION ALL

SELECT
  'annual_revenue' AS field_name,
  COUNTIF(SAFE_CAST(JSON_VALUE(original_data, '$.annual_revenue') AS INT64) IS NULL AND
          JSON_VALUE(original_data, '$.annual_revenue') IS NOT NULL) AS invalid_format,
  (SELECT COUNT(*) FROM `crm_data.invalid_contacts`)
FROM `crm_data.invalid_contacts`;


-- Динамика качества данных за период
SELECT
  DATE_TRUNC(processed_at, DAY) AS date,
  COUNT(*) AS invalid_count,
  ROUND(COUNT(*) /
    (COUNT(*) + (SELECT COUNT(*) FROM `crm_data.contacts` WHERE DATE(created_at) = DATE_TRUNC(processed_at, DAY)))
    * 100, 2) AS error_rate_pct
FROM `crm_data.invalid_contacts`
WHERE processed_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY DATE_TRUNC(processed_at, DAY)
ORDER BY date DESC;


-- Ошибки по источникам лидов
SELECT
  COALESCE(JSON_VALUE(original_data, '$.hs_analytics_source'), 'unknown') AS source,
  COUNT(*) AS invalid_count,
  COUNT(DISTINCT JSON_VALUE(original_data, '$.email')) AS affected_emails,
  COUNTIF(error_type = 'validation_error') AS validation,
  COUNTIF(error_type = 'missing_field') AS missing_field,
  COUNTIF(error_type = 'invalid_format') AS invalid_format
FROM `crm_data.invalid_contacts`
GROUP BY JSON_VALUE(original_data, '$.hs_analytics_source')
ORDER BY invalid_count DESC;
