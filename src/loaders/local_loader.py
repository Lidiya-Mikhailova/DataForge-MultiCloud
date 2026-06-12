import logging

from src.infrastructure.clients.azure_client import AzureClient

logger = logging.getLogger(__name__)


class LocalStorageLoader:
    def __init__(
        self,
        client: AzureClient,
        *,
        raw_container: str,
        processed_container: str,
        invalid_container: str,
    ) -> None:
        self._client = client
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
        logger.debug("[LOCAL] Saving %d raw records to '%s'", len(data), blob_name)
        self._client.upload_raw_data(data, blob_name, container_name=self._raw_container)

    def save_processed(self, data: list[dict], blob_name: str) -> None:
        logger.debug("[LOCAL] Saving %d processed records to '%s'", len(data), blob_name)
        self._client.upload_raw_data(data, blob_name, container_name=self._processed_container)

    def save_invalid(self, data: list[dict], blob_name: str) -> None:
        enriched = []
        for record in data:
            if isinstance(record, dict) and "error_message" in record:
                enriched.append(record)
            else:
                enriched.append(record)
        logger.debug("[LOCAL] Saving %d invalid records to '%s'", len(enriched), blob_name)
        self._client.upload_raw_data(enriched, blob_name, container_name=self._invalid_container)

    def save_raw_batch(
        self, data: list[dict], run_id: str, path_prefix: str = "ingestion"
    ) -> list[str]:
        blob_name = f"{path_prefix}/{run_id}/raw_batch.json"
        self.save_raw(data, blob_name)
        return [blob_name]

    def save_processed_batch(
        self, data: list[dict], run_id: str, path_prefix: str = "ingestion"
    ) -> list[str]:
        blob_name = f"{path_prefix}/{run_id}/processed_batch.json"
        self.save_processed(data, blob_name)
        return [blob_name]

    def save_invalid_batch(
        self, invalid_records: list[dict], run_id: str, path_prefix: str = "ingestion"
    ) -> list[str]:
        blob_name = f"{path_prefix}/{run_id}/invalid_batch.json"
        self.save_invalid(invalid_records, blob_name)
        return [blob_name]

    def close(self) -> None:
        if hasattr(self._client, "close"):
            self._client.close()
