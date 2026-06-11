import json
import logging
from abc import ABC, abstractmethod

from azure.storage.blob import BlobServiceClient, ContentSettings

logger = logging.getLogger(__name__)


class AzureClient(ABC):
    @abstractmethod
    def upload_raw_data(
        self, data: list[dict], blob_name: str, *, container_name: str | None = None
    ) -> None:
        pass

    @abstractmethod
    def list_blobs(self, prefix: str) -> list[str]:
        pass

    @abstractmethod
    def download_blob(self, blob_name: str) -> list[dict]:
        pass


class MockAzureBlobClient(AzureClient):
    def __init__(self) -> None:
        self._storage: dict[str, list[dict]] = {}

    def upload_raw_data(
        self, data: list[dict], blob_name: str, *, container_name: str | None = None
    ) -> None:
        key = f"{container_name}/{blob_name}"
        self._storage[key] = data
        logger.info(f"[MOCK] Uploaded {len(data)} records to {blob_name} (container: {container_name})")

    def list_blobs(self, prefix: str) -> list[str]:
        return [k for k in self._storage.keys() if k.startswith(prefix)]

    def download_blob(self, blob_name: str) -> list[dict]:
        for v in self._storage.values():
            return v
        return []


class AzureBlobClient(AzureClient):
    def __init__(self, connection_string: str, container_name: str = "raw") -> None:
        self._blob_service = BlobServiceClient.from_connection_string(connection_string)
        self._container_name = container_name

    def upload_raw_data(
        self, data: list[dict], blob_name: str, *, container_name: str | None = None
    ) -> None:
        try:
            target_container = container_name if container_name is not None else self._container_name
            container_client = self._blob_service.get_container_client(target_container)
            blob_client = container_client.get_blob_client(blob_name)

            content = json.dumps(data, indent=2, ensure_ascii=False)
            blob_client.upload_blob(
                content,
                overwrite=True,
                content_settings=ContentSettings(content_type="application/json"),
            )
            logger.info(f"Uploaded {len(data)} records to {blob_name}")

        except Exception as e:
            logger.exception(f"Failed to upload to Azure Blob: {e}")
            raise

    def list_blobs(self, prefix: str) -> list[str]:
        try:
            container_client = self._blob_service.get_container_client(self._container_name)
            blobs = [blob.name for blob in container_client.list_blobs(name_starts_with=prefix)]
            return sorted(blobs)

        except Exception as e:
            logger.exception(f"Failed to list blobs: {e}")
            raise

    def download_blob(self, blob_name: str) -> list[dict]:
        try:
            container_client = self._blob_service.get_container_client(self._container_name)
            blob_client = container_client.get_blob_client(blob_name)

            content = blob_client.download_blob().readall()
            data = json.loads(content)

            if isinstance(data, list):
                return data
            return [data]

        except Exception as e:
            logger.exception(f"Failed to download blob: {e}")
            raise