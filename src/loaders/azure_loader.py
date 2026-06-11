import logging
from typing import Any

from src.infrastructure.clients.azure_client import AzureBlobClient

logger = logging.getLogger(__name__)


class AzureBlobLoader:
    """
    Loader for Azure Blob Storage operations.
    
    Handles all Azure I/O: raw storage, processed data, and invalid records.
    """

    def __init__(
        self,
        blob_client: AzureBlobClient,
        *,
        raw_container: str,
        processed_container: str,
        invalid_container: str,
    ) -> None:
        self._client = blob_client
        self._raw_container = raw_container
        self._processed_container = processed_container
        self._invalid_container = invalid_container

    @property
    def raw_container(self) -> str:
        return self._raw_container

    @property
    def processed_container(self) -> str:
        return self._processed_container

    @property
    def invalid_container(self) -> str:
        return self._invalid_container

    def save_raw(self, data: list[dict], blob_name: str) -> None:
        """Save original raw data from source (e.g., HubSpot)."""
        logger.debug(f"Saving {len(data)} raw records to '{blob_name}'")
        self._client.upload_raw_data(
            data, blob_name, container_name=self._raw_container
        )

    def save_processed(self, data: list[dict], blob_name: str) -> None:
        """Save validated and cleaned data."""
        logger.debug(f"Saving {len(data)} processed records to '{blob_name}'")
        self._client.upload_raw_data(
            data, blob_name, container_name=self._processed_container
        )

    def save_invalid(self, data: list[dict], blob_name: str) -> None:
        """
        Save invalid records with error details.
        
        Each record is enriched with validation_error field.
        """
        enriched = []
        for record in data:
            if isinstance(record, dict) and "error_message" in record:
                enriched.append(record)
            else:
                enriched.append(record)
        
        logger.debug(f"Saving {len(enriched)} invalid records to '{blob_name}'")
        self._client.upload_raw_data(
            enriched, blob_name, container_name=self._invalid_container
        )

    def save_raw_batch(
        self, data: list[dict], run_id: str, path_prefix: str = "ingestion"
    ) -> list[str]:
        """Save raw data as batch, return blob names."""
        blob_name = f"{path_prefix}/{run_id}/raw_batch.json"
        self.save_raw(data, blob_name)
        return [blob_name]

    def save_processed_batch(
        self, data: list[dict], run_id: str, path_prefix: str = "ingestion"
    ) -> list[str]:
        """Save processed data as batch, return blob names."""
        blob_name = f"{path_prefix}/{run_id}/processed_batch.json"
        self.save_processed(data, blob_name)
        return [blob_name]

    def save_invalid_batch(
        self,
        invalid_records: list[dict],
        run_id: str,
        path_prefix: str = "ingestion",
    ) -> list[str]:
        """Save invalid records as batch with error details."""
        blob_name = f"{path_prefix}/{run_id}/invalid_batch.json"
        self.save_invalid(invalid_records, blob_name)
        return [blob_name]
