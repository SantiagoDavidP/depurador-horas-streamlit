from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class AzureOpenAIConfig:
    endpoint: str
    key: str
    deployment: str
    api_version: str


@dataclass
class AzureStorageConfig:
    container: Optional[str]
    connection_string: Optional[str]
    account_url: Optional[str]
    credential: Optional[str]


@dataclass
class AppSettings:
    azure_openai: AzureOpenAIConfig
    azure_storage: AzureStorageConfig
    log_level: str


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Load application settings from environment variables."""
    azure_openai = AzureOpenAIConfig(
        endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        key=os.getenv("AZURE_OPENAI_KEY", ""),
        deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
    )

    azure_storage = AzureStorageConfig(
        container=os.getenv("AZURE_STORAGE_CONTAINER"),
        connection_string=os.getenv("AZURE_STORAGE_CONNECTION_STRING"),
        account_url=os.getenv("AZURE_STORAGE_ACCOUNT_URL"),
        credential=os.getenv("AZURE_STORAGE_ACCOUNT_KEY"),
    )

    log_level = os.getenv("LOG_LEVEL", "INFO")

    return AppSettings(
        azure_openai=azure_openai,
        azure_storage=azure_storage,
        log_level=log_level,
    )