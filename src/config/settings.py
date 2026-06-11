from pydantic import BaseModel, ConfigDict, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", extra="ignore")

    HUBSPOT_ACCESS_TOKEN: str = ""
    AZURE_STORAGE_CONNECTION_STRING: str = ""
    AZURE_RAW_CONTAINER: str = "raw"
    AZURE_PROCESSED_CONTAINER: str = "processed"
    AZURE_INVALID_CONTAINER: str = "invalid"
    BIGQUERY_PROJECT_ID: str = ""
    BIGQUERY_DATASET_ID: str = ""
    POSTGRES_CONN_STRING: str = ""
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = "postgres"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    @field_validator("HUBSPOT_ACCESS_TOKEN", mode="before")
    @classmethod
    def get_hubspot_token(cls, v: str) -> str:
        import os
        return os.getenv("HUBSPOT_TOKEN", v)
