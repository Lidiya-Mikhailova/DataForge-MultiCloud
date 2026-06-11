import logging
from dataclasses import dataclass
from datetime import datetime

from src.extractors.hubspot import HubspotDataExtractor
from src.transformers.data_processor import HubspotContactTransformer
from src.loaders.azure_loader import AzureBlobLoader
from src.schemas.data_models import ValidationResult

logger = logging.getLogger(__name__)


@dataclass
class PipelineStats:
    """Statistics from pipeline execution."""
    
    total_records: int
    valid_records: int
    invalid_records: int
    raw_blob: str
    processed_blob: str | None
    invalid_blob: str | None

    def __str__(self) -> str:
        return (
            f"PipelineStats(\n"
            f"  total={self.total_records},\n"
            f"  valid={self.valid_records},\n"
            f"  invalid={self.invalid_records},\n"
            f"  raw_blob='{self.raw_blob}',\n"
            f"  processed_blob={self.processed_blob},\n"
            f"  invalid_blob={self.invalid_blob}\n"
            f")"
        )


class HubspotETLPipeline:
    """
    ETL Pipeline for HubSpot contacts with Azure Blob Storage.
    
    Data flow:
        1. Extract raw data from HubSpot → save to 'raw' container
        2. Transform & validate data
        3. Save valid (processed) data to 'processed' container
        4. Save invalid data to 'invalid' container with error details
    """

    def __init__(
        self,
        extractor: HubspotDataExtractor,
        transformer: HubspotContactTransformer,
        loader: AzureBlobLoader,
    ) -> None:
        self._extractor = extractor
        self._transformer = transformer
        self._loader = loader
        self._run_id: str = ""

    def run(self, path_prefix: str = "ingestion") -> PipelineStats:
        """
        Execute the ETL pipeline.
        
        Args:
            path_prefix: Path prefix for blob names in Azure containers
            
        Returns:
            PipelineStats with execution statistics
        """
        self._run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        logger.info("=" * 60)
        logger.info("HubspotETLPipeline started")
        logger.info(f"Run ID: {self._run_id}")
        logger.info("=" * 60)

        raw_data = self._extract()
        validation_result = self._transform(raw_data)
        self._load(raw_data, validation_result, path_prefix)

        stats = PipelineStats(
            total_records=len(raw_data),
            valid_records=len(validation_result.valid),
            invalid_records=len(validation_result.invalid),
            raw_blob=f"{path_prefix}/{self._run_id}/raw_batch.json",
            processed_blob=(
                f"{path_prefix}/{self._run_id}/processed_batch.json"
                if validation_result.valid else None
            ),
            invalid_blob=(
                f"{path_prefix}/{self._run_id}/invalid_batch.json"
                if validation_result.invalid else None
            ),
        )

        logger.info("=" * 60)
        logger.info("Pipeline completed")
        logger.info(f"Total records: {stats.total_records}")
        logger.info(f"Valid (processed): {stats.valid_records}")
        logger.info(f"Invalid: {stats.invalid_records}")
        logger.info("=" * 60)

        return stats

    def _extract(self) -> list[dict]:
        """Extract raw data from HubSpot."""
        logger.info("[1/3] Extracting data from HubSpot...")
        raw_data = self._extractor.extract()
        logger.info(f"Extracted {len(raw_data)} raw records")
        return raw_data

    def _transform(self, raw_data: list[dict]) -> ValidationResult:
        """Transform and validate data."""
        logger.info("[2/3] Transforming and validating data...")
        result = self._transformer.transform(raw_data)
        logger.info(f"Validation complete: {len(result.valid)} valid, {len(result.invalid)} invalid")
        return result

    def _load(
        self,
        raw_data: list[dict],
        validation_result: ValidationResult,
        path_prefix: str,
    ) -> None:
        """Load data to appropriate Azure containers."""
        logger.info("[3/3] Loading data to Azure Blob Storage...")

        self._loader.save_raw_batch(raw_data, self._run_id, path_prefix)
        logger.info(f"Saved {len(raw_data)} raw records to '{self._loader.raw_container}'")

        if validation_result.valid:
            processed_data = [
                contact.model_dump(mode="json") for contact in validation_result.valid
            ]
            self._loader.save_processed_batch(processed_data, self._run_id, path_prefix)
            logger.info(f"Saved {len(processed_data)} processed records to '{self._loader.processed_container}'")

        if validation_result.invalid:
            invalid_data = [
                {
                    "original_data": record.original_data,
                    "error_message": record.error_message,
                    "error_type": record.error_type,
                }
                for record in validation_result.invalid
            ]
            self._loader.save_invalid_batch(invalid_data, self._run_id, path_prefix)
            logger.info(f"Saved {len(invalid_data)} invalid records to '{self._loader.invalid_container}'")
