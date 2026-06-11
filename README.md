# DataForge-MultiCloud — ETL Pipeline

[![CI/CD](https://github.com/YOUR_ORG/dataforge-multicloud/actions/workflows/etl.yml/badge.svg)](https://github.com/YOUR_ORG/dataforge-multicloud/actions/workflows/etl.yml)


---

## Architecture

```
HubSpot CRM ──► Extract ──► Azure Blob ──► Validate (Pydantic)
                                              │
                                    ┌─────────┴─────────┐
                                    ▼                   ▼
                              Valid contacts     Invalid records
                                    │                   │
                                    ▼                   ▼
                              BigQuery Raw ──► BigQuery Core ──► BI Marts
                                              (MERGE UPSERT)     (6 views)
```

---

## Data Flow (Medallion Architecture)

| Layer | Stage | What happens |
|-------|-------|-------------|
| **Bronze** | **Extract** | `HubspotDataExtractor` pulls contacts from HubSpot API (or mock) |
| **Bronze** | **Backup** | Raw data saved to Azure Blob: `raw/`, `processed/`, `invalid/` containers |
| **Bronze** | **Validate** | `HubspotContactTransformer` validates each contact (email, name, types) → `ValidationResult(valid, invalid)` |
| **Bronze** | **Load Raw** | Valid → `crm_data_raw.contacts_raw`, Invalid → `crm_data_raw.contacts_quarantine` (WRITE_APPEND) |
| **Silver** | **Core** | MERGE into `crm_data_core.core_contacts` with dedup (Python or dbt) |
| **Gold** | **Mart** | 6 BI-ready views: lead analytics, sales funnel, industry, conversion, data quality, daily trends |

---

## Stack

| Component | Technology |
|-----------|-----------|
| **Language** | Python 3.11+ |
| **CRM** | HubSpot API v3 |
| **Validation** | Pydantic |
| **Raw Storage** | Azure Blob Storage |
| **Warehouse** | Google BigQuery (raw → core → mart) |
| **Transform** | dbt / Python MERGE |
| **Orchestration** | Apache Airflow 3.x |
| **Containerization** | Docker / docker-compose (Airflow, PostgreSQL, ETL) |

---

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in tokens
python etl_pipeline.py                # mock ETL
USE_DBT=true python etl_pipeline.py   # with dbt
export AIRFLOW_HOME=./airflow_home && airflow standalone
```

## Docker

```bash
docker-compose up --build
```

Database (PostgreSQL 15) runs as a Docker service — used by Airflow as its metadata backend and available for local ETL development. The pipeline defaults to DuckDB/Parquet in `STORAGE_MODE=local` for zero-infra dev, with BigQuery as the production warehouse. Set `STORAGE_MODE=cloud` to use PostgreSQL for intermediate storage.

## CI/CD Pipeline (GitHub Actions)

| Stage | Description |
|-------|-------------|
| **Lint** | Ruff linting + mypy type check + Python syntax check on all source files |
| **Test** | pytest (4 tests) + ETL pipeline end-to-end with mock data |
| **Docker** | Builds Docker image (with layer caching via GitHub Actions) |
| **dbt** | Validates dbt project — `dbt parse` for syntax correctness |
| **Compose** | Validates `docker-compose.yml` configuration |

### Airflow DAG Tasks

The DAG `hubspot_etl_pipeline` is split into 3 sequential tasks:

```
extract → validate → load_and_transform
```

Each task can be retried independently in the Airflow UI. The `load_and_transform` task combines BigQuery load + dbt/Python MERGE to reduce API round-trips and avoid potential task instance lookup failures.

The pipeline runs on every push/PR to `main`/`master` and can be triggered manually via `workflow_dispatch`.

---

## Project Structure

```
├── src/
│   ├── config/            Pydantic Settings
│   ├── core/              Extractor / Transformer / Loader abstractions
│   ├── extractors/        HubSpot, Azure implementations
│   ├── transformers/      Pydantic validation
│   ├── loaders/           Azure, Postgres, BigQuery, Local
│   ├── infrastructure/    Clients (HubSpot, Azure, Postgres)
│   ├── schemas/           Contact, InvalidRecord models
│   ├── warehouse/         BigQuery client, loader, queries
│   └── utils/
├── dags/                  Airflow DAG
├── transform/             dbt project (staging → core → mart)
├── airflow_home/
└── data/                  Local storage (DuckDB/Parquet)
```

---

## Env Variables

| Variable | Default |
|----------|---------|
| `HUBSPOT_ACCESS_TOKEN` | — |
| `AZURE_STORAGE_CONNECTION_STRING` | — |
| `GOOGLE_APPLICATION_CREDENTIALS` | `src/config/gcp_credentials.json` |
| `BIGQUERY_PROJECT_ID` | `dataforge-multicloud` |
| `USE_MOCK` | `true` |
| `STORAGE_MODE` | `local` |
| `USE_DBT` | `false` |

---

> **P.S. Why Azure instead of DuckDB?**  
> DuckDB was used initially for local development — lightweight, no infra needed. In production, it was replaced with **Azure Blob Storage** for reliability, centralized access, and lower operational costs. DuckDB is still available in `STORAGE_MODE=local` (data → Parquet via DuckDB), ideal for dev/testing without cloud resources.
>
> **Optimization note:** The migration from DuckDB to Azure Blob Storage was part of a broader optimization — unified backup strategy, centralized blob lifecycle management, and reduced local storage footprint. The modular `Extractor → Transformer → Loader` abstraction allowed this swap without touching core logic, and the same pattern applies to any future storage or source changes.
>
> The pipeline core is built on `Extractor → Transformer → Loader` abstractions, making it **modular** — swapping sources (Salesforce, Zoho), storage backends, or transform engines requires zero changes to core logic. This makes the project easy to scale and adapt.
