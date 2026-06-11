import logging
from typing import Optional

from src.core.interfaces import Extractor
from src.infrastructure.clients.azure_client import AzureClient

logger = logging.getLogger(__name__)


class AzureRawExtractor(Extractor):
    def __init__(self, azure_client: AzureClient) -> None:
        self._azure_client = azure_client

    def extract(self, prefix: Optional[str] = "hubspot/contacts") -> list[dict]:
        try:
            logger.info(f"Listing blobs with prefix: {prefix}")
            blobs = self._azure_client.list_blobs(prefix=prefix)
            logger.info(f"Found {len(blobs)} blobs")

            if not blobs:
                logger.warning(f"No blobs found for prefix {prefix}")
                return []

            latest_blob = sorted(blobs, reverse=True)[0]
            logger.info(f"Downloading latest blob: {latest_blob}")
            data = self._azure_client.download_blob(blob_name=latest_blob)
            logger.info(f"Downloaded {len(data)} records from {latest_blob}")

            return data

        except Exception as e:
            logger.exception(f"Azure raw extraction failed: {e}")
            raise