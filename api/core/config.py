"""Application settings loaded from environment variables using pydantic-settings."""

from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with safe defaults for development/test startup."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # Application
    APP_NAME: str = "BONAPHARM - Pedidos y Devoluciones API"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = Field(default="development")
    DEBUG: bool = Field(default=True)

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/bonapharm_pedidos",
        description="Async database connection URL",
    )

    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000"],
    )

    # Auth / JWT
    SECRET_KEY: str = Field(
        default="dev-secret-key-change-in-production",
        description="JWT secret key -- MUST be overridden in production",
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)

    # Microsoft Entra ID (Azure AD)
    ENTRA_ID_CLIENT_ID: str = Field(default="")
    ENTRA_ID_SECRET_KEY: str = Field(default="")
    ENTRA_ID_TENANT_ID: str = Field(default="")

    # External APIs
    DATAVERSE_ENVIRONMENT_URL: str = Field(default="")
    SAP_API_BASE_URL: str = Field(default="https://api.sap.bonapharm.com/v1")
    SAP_API_KEY: str = Field(default="")
    SHAREPOINT_SITE_URL: str = Field(default="")

    # SMTP
    SMTP_HOST: str = Field(default="localhost")
    SMTP_PORT: int = Field(default=587)
    SMTP_USER: str = Field(default="")
    SMTP_PASSWORD: str = Field(default="")
    SMTP_FROM_EMAIL: str = Field(default="noreply@bonapharm.com")
    SMTP_TLS: bool = Field(default=True)

    # IGV (Peruvian tax)
    IGV_RATE: float = Field(default=0.18, description="Impuesto General a las Ventas")

    # Commission percentages
    COMISION_DIMEXA_PCT: float = Field(default=0.10)
    COMISION_QUIMICA_PCT: float = Field(default=0.13)


settings = Settings()
