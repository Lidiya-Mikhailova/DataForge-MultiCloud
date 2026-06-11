import json
import logging
import os
from typing import Optional

import duckdb

from src.infrastructure.clients.azure_client import AzureClient

logger = logging.getLogger(__name__)


class LocalStorageClient(AzureClient):
    def __init__(self, data_dir: str = "data") -> None:
        self._data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self._db_path = os.path.join(data_dir, "lakehouse.duckdb")
        self._conn = duckdb.connect(self._db_path)
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS blob_catalog (
                blob_key VARCHAR PRIMARY KEY,
                container VARCHAR,
                blob_name VARCHAR,
                record_count INTEGER,
                file_path VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    def upload_raw_data(
        self, data: list[dict], blob_name: str, *, container_name: Optional[str] = None
    ) -> None:
        container = container_name or "default"
        key = f"{container}/{blob_name}"

        parquet_path = os.path.join(self._data_dir, "records", container, blob_name.replace(".json", ".parquet"))
        os.makedirs(os.path.dirname(parquet_path), exist_ok=True)

        self._conn.execute("DROP TABLE IF EXISTS _upload_batch")
        self._conn.execute("CREATE TABLE _upload_batch AS SELECT * FROM (VALUES (NULL::JSON)) WHERE 1=0")
        for record in data:
            self._conn.execute(
                "INSERT INTO _upload_batch SELECT CAST(? AS JSON)",
                [json.dumps(record, ensure_ascii=False, default=str)],
            )

        self._conn.execute(
            f"COPY _upload_batch TO '{parquet_path}' (FORMAT PARQUET, COMPRESSION ZSTD)"
        )
        self._conn.execute("DROP TABLE IF EXISTS _upload_batch")

        self._conn.execute(
            """INSERT OR REPLACE INTO blob_catalog (blob_key, container, blob_name, record_count, file_path)
               VALUES (?, ?, ?, ?, ?)""",
            [key, container, blob_name, len(data), parquet_path],
        )

        logger.info("[LOCAL] Stored %d records to Parquet: '%s'", len(data), parquet_path)

        json_dir = os.path.join(self._data_dir, "json", container, os.path.dirname(blob_name))
        os.makedirs(json_dir, exist_ok=True)
        json_path = os.path.join(self._data_dir, "json", container, blob_name)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        logger.info("[LOCAL] JSON backup saved to '%s'", json_path)

    def list_blobs(self, prefix: str) -> list[str]:
        rows = self._conn.execute(
            "SELECT blob_key FROM blob_catalog WHERE blob_key LIKE ? ORDER BY blob_key",
            [f"{prefix}%"],
        ).fetchall()
        return [r[0] for r in rows]

    def download_blob(self, blob_name: str) -> list[dict]:
        row = self._conn.execute(
            "SELECT file_path FROM blob_catalog WHERE blob_name = ?",
            [blob_name],
        ).fetchone()
        if row is None:
            json_path = os.path.join(self._data_dir, "json", "default", blob_name)
            if os.path.exists(json_path):
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    return data
                return [data]
            logger.warning("Blob not found locally: %s", blob_name)
            return []

        parquet_path = row[0]
        df = self._conn.execute(f"SELECT * FROM '{parquet_path}'").fetchdf()
        return df.to_dict(orient="records")

    def close(self) -> None:
        self._conn.close()
