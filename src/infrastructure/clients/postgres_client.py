import logging
from typing import Optional

import psycopg2


logger = logging.getLogger(__name__)


class PostgresClient:
    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
    ) -> None:
        self._host = host
        self._port = port
        self._database = database
        self._user = user
        self._password = password

    def execute_query(self, query: str, params: Optional[tuple] = None) -> None:
        conn = None
        try:
            conn = psycopg2.connect(
                host=self._host,
                port=self._port,
                database=self._database,
                user=self._user,
                password=self._password,
            )
            with conn.cursor() as cursor:
                cursor.execute(query, params)
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.exception(f"Query execution failed: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def create_table_if_not_exists(self) -> None:
        query = """
        CREATE TABLE IF NOT EXISTS contacts (
            contact_id VARCHAR(255) PRIMARY KEY,
            email VARCHAR(255) NOT NULL,
            first_name VARCHAR(255),
            last_name VARCHAR(255),
            created_at TIMESTAMP
        );
        """
        self.execute_query(query)
        logger.info("Table 'contacts' ready")