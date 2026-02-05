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
class AzureADConfig:
    """Configuración de autenticación Azure AD."""
    client_id: Optional[str]
    client_secret: Optional[str]
    tenant_id: Optional[str]
    redirect_uri: Optional[str]
    allowed_group_id: Optional[str]
    enabled: bool


@dataclass
class AppSettings:
    azure_openai: AzureOpenAIConfig
    azure_storage: AzureStorageConfig
    azure_ad: AzureADConfig
    log_level: str


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Load application settings from environment variables."""
    # Validación temprana de credenciales críticas
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    key = os.getenv("AZURE_OPENAI_KEY", "")
    
    # Advertir si las credenciales no están configuradas (no fallar para no romper desarrollo local)
    if not endpoint or not key:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            "ADVERTENCIA: Azure OpenAI no está completamente configurado. "
            "Defina AZURE_OPENAI_ENDPOINT y AZURE_OPENAI_KEY en variables de entorno. "
            "Las funciones que requieran LLM fallarán."
        )
    
    azure_openai = AzureOpenAIConfig(
        endpoint=endpoint,
        key=key,
        deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
    )

    azure_storage = AzureStorageConfig(
        container=os.getenv("AZURE_STORAGE_CONTAINER"),
        connection_string=os.getenv("AZURE_STORAGE_CONNECTION_STRING"),
        account_url=os.getenv("AZURE_STORAGE_ACCOUNT_URL"),
        credential=os.getenv("AZURE_STORAGE_ACCOUNT_KEY"),
    )

    # Azure AD Authentication
    azure_ad_enabled = os.getenv("AZURE_AD_AUTH_ENABLED", "false").lower() == "true"
    azure_ad = AzureADConfig(
        client_id=os.getenv("AZURE_AD_CLIENT_ID"),
        client_secret=os.getenv("AZURE_AD_CLIENT_SECRET"),
        tenant_id=os.getenv("AZURE_AD_TENANT_ID"),
        redirect_uri=os.getenv("AZURE_AD_REDIRECT_URI", "http://localhost:8501"),
        allowed_group_id=os.getenv("AZURE_AD_ALLOWED_GROUP_ID"),
        enabled=azure_ad_enabled,
    )

    log_level = os.getenv("LOG_LEVEL", "INFO")

    return AppSettings(
        azure_openai=azure_openai,
        azure_storage=azure_storage,
        azure_ad=azure_ad,
        log_level=log_level,
    )