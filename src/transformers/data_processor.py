import logging
from typing import Optional

from pydantic import ValidationError

from src.schemas.data_models import (
    CsvContactRaw,
    HubspotContactRaw,
    Contact,
    InvalidRecord,
    ValidationResult,
)

logger = logging.getLogger(__name__)


def is_csv_format(data: dict) -> bool:
    return "contact_id" in data and "first_name" in data


class HubspotContactTransformer:
    """
    Transformer for HubSpot contact data.
    
    Validates raw data using Pydantic and separates into valid and invalid records.
    Supports both HubSpot API format (nested properties) and CSV format (flat).
    Returns ValidationResult - NO I/O operations.
    """

    def transform(self, data: list[dict]) -> ValidationResult:
        valid: list[Contact] = []
        invalid: list[InvalidRecord] = []

        if not data:
            return ValidationResult(valid=valid, invalid=invalid)

        csv_format = is_csv_format(data[0])

        for idx, item in enumerate(data):
            if csv_format:
                self._transform_csv_record(item, valid, invalid, idx)
            else:
                self._transform_api_record(item, valid, invalid, idx)

        logger.info(
            f"Transform complete: {len(valid)} valid, {len(invalid)} invalid"
        )
        return ValidationResult(valid=valid, invalid=invalid)

    def _transform_csv_record(
        self,
        item: dict,
        valid: list[Contact],
        invalid: list[InvalidRecord],
        idx: int,
    ) -> None:
        try:
            raw_contact = CsvContactRaw.model_validate(item)
        except ValidationError as e:
            logger.debug(f"Record {idx} failed CsvContactRaw validation: {e}")
            invalid.append(
                InvalidRecord(
                    original_data=item,
                    error_message=e.json(),
                    error_type="ValidationError",
                )
            )
            return

        if not raw_contact.email or "@" not in raw_contact.email:
            invalid.append(
                InvalidRecord(
                    original_data=item,
                    error_message="Field 'email' is required and must be valid",
                    error_type="MissingEmail",
                )
            )
            return

        try:
            contact = Contact(
                contact_id=raw_contact.contact_id,
                email=raw_contact.email,
                first_name=raw_contact.first_name,
                last_name=raw_contact.last_name,
                company_name=raw_contact.company_name,
                job_title=raw_contact.job_title,
                annual_revenue=raw_contact.annual_revenue,
                created_at=raw_contact.created_at,
            )
            valid.append(contact)
        except ValidationError as e:
            logger.debug(f"Record {idx} failed Contact validation: {e}")
            invalid.append(
                InvalidRecord(
                    original_data=item,
                    error_message=str(e),
                    error_type="ValidationError",
                )
            )

    def _transform_api_record(
        self,
        item: dict,
        valid: list[Contact],
        invalid: list[InvalidRecord],
        idx: int,
    ) -> None:
        try:
            raw_contact = HubspotContactRaw.model_validate(item)
        except ValidationError as e:
            logger.debug(f"Record {idx} failed HubspotContactRaw validation: {e}")
            invalid.append(
                InvalidRecord(
                    original_data=item,
                    error_message=e.json(),
                    error_type="ValidationError",
                )
            )
            return

        if not raw_contact.properties.email:
            invalid.append(
                InvalidRecord(
                    original_data=item,
                    error_message="Field 'properties.email' is required and cannot be empty",
                    error_type="MissingEmail",
                )
            )
            return

        try:
            from datetime import datetime
            createdate = raw_contact.properties.createdate
            if createdate:
                try:
                    createdate = createdate.replace("Z", "+00:00")
                    if createdate.endswith(" +0000"):
                        createdate = createdate.replace(" +0000", "+00:00")
                    createdate = datetime.fromisoformat(createdate)
                except (ValueError, TypeError):
                    createdate = None
            
            contact = Contact(
                contact_id=raw_contact.id,
                email=raw_contact.properties.email,
                first_name=raw_contact.properties.firstname,
                last_name=raw_contact.properties.lastname,
                company_name=raw_contact.properties.company,
                job_title=raw_contact.properties.jobtitle,
                industry=raw_contact.properties.industry,
                annual_revenue=int(raw_contact.properties.annualrevenue) if raw_contact.properties.annualrevenue else None,
                numberofemployees=int(raw_contact.properties.numberofemployees) if raw_contact.properties.numberofemployees else None,
                created_at=createdate,
                lead_status=raw_contact.properties.leadstatus,
                hs_analytics_source=raw_contact.properties.hs_analytics_source,
                hs_analytics_source_data_1=raw_contact.properties.hs_analytics_source_data_1,
            )
            valid.append(contact)
        except ValidationError as e:
            logger.debug(f"Record {idx} failed Contact validation: {e}")
            invalid.append(
                InvalidRecord(
                    original_data=item,
                    error_message=str(e),
                    error_type="ValidationError",
                )
            )
