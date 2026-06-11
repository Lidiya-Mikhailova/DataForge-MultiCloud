from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator, ConfigDict, Field


class HubspotProperties(BaseModel):
    email: Optional[str] = None
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    createdate: Optional[str] = None
    company: Optional[str] = None
    jobtitle: Optional[str] = None
    industry: Optional[str] = None
    annualrevenue: Optional[str] = None
    numberofemployees: Optional[str] = None
    hs_analytics_source: Optional[str] = None
    hs_analytics_source_data_1: Optional[str] = None
    leadstatus: Optional[str] = None


class HubspotContactRaw(BaseModel):
    id: str
    properties: HubspotProperties


class CsvContactRaw(BaseModel):
    contact_id: str
    email: str
    first_name: str
    last_name: str
    company_name: str
    job_title: str
    annual_revenue: str
    created_at: str


class Contact(BaseModel):
    model_config = ConfigDict(str_to_lower=True)

    contact_id: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    industry: Optional[str] = None
    annual_revenue: Optional[int] = None
    numberofemployees: Optional[int] = None
    created_at: Optional[datetime] = None
    lastmodifieddate: Optional[datetime] = None

    @field_validator("lastmodifieddate", mode="before")
    @classmethod
    def parse_lastmodifieddate(cls, v: Optional[str]) -> Optional[datetime]:
        if not v:
            return None
        v = str(v).strip()
        if not v:
            return None
        if "T" not in v:
            return None
        try:
            v = v.replace("Z", "+00:00")
            if v.endswith(" +0000"):
                v = v.replace(" +0000", "+00:00")
            return datetime.fromisoformat(v)
        except (ValueError, TypeError):
            return None
    lead_status: Optional[str] = None
    hs_analytics_source: Optional[str] = None
    hs_analytics_source_data_1: Optional[str] = None
    processed_at: Optional[datetime] = None
    run_id: Optional[str] = None

    @field_validator("created_at", mode="before")
    @classmethod
    def parse_created_at(cls, v: Optional[str]) -> Optional[datetime]:
        if not v:
            return None
        v = str(v).strip()
        if not v:
            return None
        if "T" not in v:
            return None
        try:
            v = v.replace("Z", "+00:00")
            if v.endswith(" +0000"):
                v = v.replace(" +0000", "+00:00")
            return datetime.fromisoformat(v)
        except (ValueError, TypeError):
            return None

    @field_validator("annual_revenue", mode="before")
    @classmethod
    def parse_revenue(cls, v) -> Optional[int]:
        if not v:
            return None
        if isinstance(v, int):
            return v
        return int(v)


class InvalidRecord(BaseModel):
    original_data: dict
    error_message: str
    error_type: str


class ValidationResult(BaseModel):
    valid: list[Contact]
    invalid: list[InvalidRecord]
