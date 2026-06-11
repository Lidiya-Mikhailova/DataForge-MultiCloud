import logging
from typing import List

from src.core.interfaces import Loader
from src.schemas.data_models import Contact

logger = logging.getLogger(__name__)


class MockPostgresLoader(Loader):
    def __init__(self) -> None:
        self._data: List[Contact] = []

    def load(self, data: List[Contact]) -> None:
        logger.info(f"Mock load: storing {len(data)} records in memory")
        self._data = data
        logger.info("Mock load completed successfully")

    def get_data(self) -> List[Contact]:
        return self._data
