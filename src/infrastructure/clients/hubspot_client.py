import logging
from abc import ABC, abstractmethod
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class HubspotClient(ABC):
    @abstractmethod
    def get_contacts(self, since: Optional[str] = None) -> list[dict]:
        pass


class MockHubspotClient(HubspotClient):
    def __init__(self) -> None:
        self._mock_data = [
            {
                "id": "contact_1",
                "properties": {
                    "email": "test1@example.com",
                    "firstname": "John",
                    "lastname": "Doe",
                    "createdate": "2024-01-15T10:30:00Z",
                },
            },
            {
                "id": "contact_2",
                "properties": {
                    "email": "test2@example.com",
                    "firstname": "Jane",
                    "lastname": "Smith",
                    "createdate": "2024-02-20T14:45:00Z",
                },
            },
            {
                "id": "contact_3",
                "properties": {
                    "email": "invalid-email",
                    "firstname": "Invalid",
                    "lastname": "User",
                },
            },
        ]

    def get_contacts(self, since: Optional[str] = None) -> list[dict]:
        logger.info("Returning mock contacts data")
        return self._mock_data


class HubspotApiClient(HubspotClient):
    def __init__(self, access_token: str) -> None:
        self._access_token = access_token
        self._base_url = "https://api.hubapi.com"

    def get_contacts(self, since: Optional[str] = None) -> list[dict]:
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

        params = {"limit": 100}
        if since:
            params["created__gte"] = since

        all_contacts = []

        try:
            while True:
                response = requests.get(
                    f"{self._base_url}/crm/v3/objects/contacts",
                    headers=headers,
                    params=params,
                    timeout=30,
                )
                response.raise_for_status()
                data = response.json()

                all_contacts.extend(data.get("results", []))

                if "paging" not in data:
                    break
                params["after"] = data["paging"]["next"]["after"]

            logger.info(f"Fetched {len(all_contacts)} contacts from HubSpot")
            return all_contacts

        except Exception as e:
            logger.exception(f"Failed to fetch contacts from HubSpot: {e}")
            raise