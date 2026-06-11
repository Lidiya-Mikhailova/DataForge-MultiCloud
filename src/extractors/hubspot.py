import logging
from datetime import datetime
from typing import Optional

from src.core.interfaces import Extractor
from src.infrastructure.clients.hubspot_client import HubspotClient

logger = logging.getLogger(__name__)


class HubspotDataExtractor(Extractor):
    """Extracts raw contact data from HubSpot CRM."""

    def __init__(self, hubspot_client: HubspotClient) -> None:
        self._hubspot_client = hubspot_client

    def extract(self, since_date: Optional[datetime] = None) -> list[dict]:
        """
        Extract contacts from HubSpot.
        
        Args:
            since_date: Optional datetime to fetch only contacts created after this date
            
        Returns:
            List of raw contact dictionaries
        """
        try:
            since_param: Optional[str] = None
            if since_date:
                since_param = since_date.isoformat()
                logger.info(f"Starting incremental extraction since {since_param}")
            else:
                logger.info("Starting full extraction (no since_date provided)")

            raw_data = self._hubspot_client.get_contacts(since=since_param)
            logger.info(f"Extracted {len(raw_data)} contacts from HubSpot")

            return raw_data

        except Exception as e:
            logger.exception(f"Extraction failed: {e}")
            raise
