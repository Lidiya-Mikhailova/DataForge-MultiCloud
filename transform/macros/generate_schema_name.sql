{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- set default_schema = target.schema -%}
    {%- set prefix = var('stg_dataset', 'crm_data_stg') -%}

    {%- if custom_schema_name is none -%}
        {{ default_schema }}
    {%- elif custom_schema_name == 'STG' -%}
        {{ prefix }}
    {%- elif custom_schema_name == 'CORE' -%}
        {{ var('core_dataset', 'crm_data_core') }}
    {%- elif custom_schema_name == 'MART' -%}
        {{ var('mart_dataset', 'crm_data_mart') }}
    {%- else -%}
        {{ custom_schema_name | lower }}
    {%- endif -%}
{%- endmacro -%}
