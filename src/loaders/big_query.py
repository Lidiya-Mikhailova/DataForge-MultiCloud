import logging
from typing import Optional

logger = logging.getLogger(__name__)


class BigQueryLoader:
    def __init__(
        self,
        project_id: Optional[str] = None,
        dataset_id: Optional[str] = None,
        credentials_path: Optional[str] = None,
    ) -> None:
        logger.warning(
            "BigQueryLoader is DEPRECATED. Use src.warehouse.WarehouseLoader instead. "
            "This class uses legacy WRITE_TRUNCATE approach."
        )
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.credentials_path = credentials_path

    def load_data(self, table_name: str, data_frame) -> None:
        logger.warning(
            "BigQueryLoader.load_data() is DEPRECATED. "
            "Use WarehouseLoader.load_valid_to_raw() + merge_to_core() instead."
        )
        logger.info(
            "Would load %d rows to %s.%s (skipped — use WarehouseLoader)",
            len(data_frame), self.dataset_id, table_name,
        )
