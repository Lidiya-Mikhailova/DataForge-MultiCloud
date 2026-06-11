import logging
from typing import List

from src.core.interfaces import Loader
from src.infrastructure.clients.postgres_client import PostgresClient
from src.schemas.data_models import Contact

logger = logging.getLogger(__name__)


class PostgresLoader(Loader):
    def __init__(self, postgres_client: PostgresClient) -> None:
        self._client = postgres_client

    def load(self, data: List[Contact]) -> None:
        logger.info(f"Starting load of {len(data)} records to Postgres")

        try:
            self._client.create_table_if_not_exists()

            for contact in data:
                query = """
                INSERT INTO contacts (contact_id, email, first_name, last_name, created_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (contact_id) DO UPDATE SET
                    email = EXCLUDED.email,
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    created_at = EXCLUDED.created_at;
                """
                self._client.execute_query(
                    query,
                    (
                        contact.contact_id,
                        str(contact.email),
                        contact.first_name,
                        contact.last_name,
                        contact.created_at,
                    ),
                )

            logger.info(f"Successfully loaded {len(data)} records to Postgres")

        except Exception as e:
            logger.exception(f"Postgres load failed: {e}")
            raise