from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import patch

import pytest


@pytest.fixture
def mock_settings(monkeypatch):
    monkeypatch.setenv("BIGQUERY_PROJECT_ID", "")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    monkeypatch.setenv("HUBSPOT_ACCESS_TOKEN", "")
    monkeypatch.delenv("BIGQUERY_PROJECT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    from etl_pipeline import Settings
    return Settings(
        USE_MOCK=True,
        STORAGE_MODE="local",
        USE_DBT=False,
        BIGQUERY_PROJECT_ID="",
        LOCAL_DATA_DIR=tempfile.mkdtemp(),
    )


def test_extract_stage(mock_settings):
    from etl_pipeline import create_hubspot_extractor, create_local_loader, stage_extract_and_backup

    extractor = create_hubspot_extractor(mock_settings)
    loader = create_local_loader(mock_settings)

    run_id, raw_data, blob_name = stage_extract_and_backup(
        mock_settings, extractor, loader, "test/contacts"
    )

    assert run_id is not None
    assert len(raw_data) > 0
    assert blob_name is not None

    data_path = os.path.join(mock_settings.LOCAL_DATA_DIR, run_id, "raw_data.json")
    assert os.path.exists(data_path)
    with open(data_path) as f:
        loaded = json.load(f)
    assert len(loaded) == len(raw_data)


def test_validate_stage(mock_settings):
    from etl_pipeline import (
        create_hubspot_extractor, create_local_loader,
        stage_extract_and_backup, stage_validate,
    )
    from src.transformers.data_processor import HubspotContactTransformer

    extractor = create_hubspot_extractor(mock_settings)
    loader = create_local_loader(mock_settings)
    transformer = HubspotContactTransformer()

    run_id, raw_data, _ = stage_extract_and_backup(mock_settings, extractor, loader, "test/contacts")
    validation_result, valid_count, invalid_count = stage_validate(
        mock_settings, transformer, loader, raw_data, run_id, "test/contacts"
    )

    assert valid_count + invalid_count == len(raw_data)
    assert valid_count >= 0
    assert invalid_count >= 0

    data_dir = os.path.join(mock_settings.LOCAL_DATA_DIR, run_id)
    assert os.path.exists(os.path.join(data_dir, "valid_contacts.json"))
    assert os.path.exists(os.path.join(data_dir, "invalid_records.json"))


def test_full_pipeline_mock(mock_settings):
    from etl_pipeline import (
        create_hubspot_extractor, create_local_loader,
        create_warehouse, run_etl_pipeline,
    )
    from src.transformers.data_processor import HubspotContactTransformer

    extractor = create_hubspot_extractor(mock_settings)
    transformer = HubspotContactTransformer()
    loader = create_local_loader(mock_settings)
    warehouse = create_warehouse(mock_settings)

    stats = run_etl_pipeline(
        extractor=extractor,
        transformer=transformer,
        azure_loader=loader,
        warehouse=warehouse,
        settings=mock_settings,
        path_prefix="test/contacts",
    )

    assert stats.run_id is not None
    assert stats.total_records > 0
    assert stats.valid_records + stats.invalid_records == stats.total_records
    assert not stats.dbt_run
    assert stats.core_merged == 0  # no BigQuery configured


def test_pipeline_stats():
    from etl_pipeline import PipelineStats

    stats = PipelineStats(
        run_id="test_001",
        total_records=100,
        valid_records=75,
        invalid_records=25,
        raw_loaded=75,
        quarantined=25,
        core_merged=60,
    )

    assert stats.run_id == "test_001"
    assert stats.total_records == 100
    assert stats.valid_records == 75
    assert stats.invalid_records == 25
    assert stats.raw_loaded == 75
    assert stats.core_merged == 60
