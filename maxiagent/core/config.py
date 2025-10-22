"""
Configuration Module

Uses Pydantic BaseSettings for:
- Automatic environment variable loading
- Type validation
- Clear documentation of required variables
- Computed fields for derived values
"""
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class Settings(BaseSettings):
    """
    Application configuration with automatic environment variable loading.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"  # Ignorar variables extra en .env
    )

    # ==================== Flask Configuration ====================
    FLASK_ENV: Literal["dev", "prod"] = Field(
        default="dev",
        description="Flask environment (dev or prod)"
    )

    ENV: Literal["dev", "prod"] = Field(
        default="dev",
        description="Environment (dev or prod) - alias for FLASK_ENV"
    )

    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] | None = Field(
        default=None,
        description="Logging level for the application (auto: DEBUG for dev, INFO for prod)"
    )

    @computed_field
    @property
    def EFFECTIVE_LOG_LEVEL(self) -> str:
        """
        Determine the effective log level.

        If LOG_LEVEL is explicitly set, use it.
        Otherwise, use DEBUG for dev environment and INFO for prod.

        Returns:
            The effective log level as a string
        """
        if self.LOG_LEVEL:
            return self.LOG_LEVEL
        # Auto-configure based on environment
        return "DEBUG" if self.ENV == "dev" else "INFO"

    # ==================== Google Cloud Configuration ====================
    GOOGLE_CLOUD_PROJECT: str | None = Field(
        default=None,
        description="Google Cloud Project ID"
    )

    GOOGLE_CLOUD_LOCATION: str = Field(
        default="us-central1",
        description="Google Cloud region/location"
    )

    CLOUD_VAR: str | None = Field(
        default=None,
        description="Variable defined in Cloud Run to detect if running in cloud"
    )

    # ==================== Agent Configuration ====================
    AGENT_ENGINE_ID: str | None = Field(
        default=None,
        description="Agent Engine ID for LLM Orchestrator"
    )

    ROOT_AGENT_MODEL: str | None = Field(
        default=None,
        description="Root agent model name"
    )

    # ==================== RAG Configuration ====================
    RAG_CORPUS: str | None = Field(
        default=None,
        description="RAG corpus identifier"
    )

    # ==================== Search Configuration ====================
    GOOGLE_SEARCH_API_KEY: str | None = Field(
        default=None,
        description="Google Search API key"
    )

    GOOGLE_CSE_ID: str | None = Field(
        default=None,
        description="Google Custom Search Engine ID"
    )

    GOOGLE_MAPS_API_KEY: str | None = Field(
        default=None,
        description="Google Maps Platform API key (Places API + Geocoding API)"
    )

    # ==================== Embedding Configuration ====================
    EMBEDDING_MODEL_NAME: str | None = Field(
        default=None,
        description="Name of the embedding model to use"
    )

    # ==================== Storage Configuration ====================
    ADK_ARTIFACT_BUCKET: str | None = Field(
        default=None,
        description="Google Cloud Storage bucket for ADK artifacts"
    )

    # ==================== Development API URLs ====================
    URL_CALCULADORA_DEV: str | None = Field(
        default=None,
        description="Calculator API URL for development"
    )

    KEY_CALCULADORA_DEV: str | None = Field(
        default=None,
        description="Calculator API key for development"
    )

    URL_ORIGINADOR_DEV: str | None = Field(
        default=None,
        description="Originator API URL for development"
    )

    KEY_ORIGINADOR_DEV: str | None = Field(
        default=None,
        description="Originator API key for development"
    )

    API_MAXIKASH_DEV: str | None = Field(
        default=None,
        description="Maxikash API URL for development"
    )

    URL_DATA_MAXI_DEV: str | None = Field(
        default=None,
        description="Data Maxi URL for development"
    )

    USRNAME_DATA_MAXI_DEV: str | None = Field(
        default=None,
        description="Data Maxi username for development"
    )

    PASSWORD_DATA_MAXI_DEV: str | None = Field(
        default=None,
        description="Data Maxi password for development"
    )

    AGENT_CHAT_URL_DEV: str | None = Field(
        default=None,
        description="Agent chat URL for development"
    )

    URL_CREDITOS_MAXI_DEV: str | None = Field(
        default=None,
        description="Creditos Maxi URL for development"
    )

    USRNAME_CREDITOS_MAXI_DEV: str | None = Field(
        default=None,
        description="Creditos Maxi username for development"
    )

    PASSWORD_CREDITOS_MAXI_DEV: str | None = Field(
        default=None,
        description="Creditos Maxi password for development"
    )

    # ==================== Production API URLs ====================
    URL_CALCULADORA_PROD: str | None = Field(
        default=None,
        description="Calculator API URL for production"
    )

    KEY_CALCULADORA_PROD: str | None = Field(
        default=None,
        description="Calculator API key for production"
    )

    URL_ORIGINADOR_PROD: str | None = Field(
        default=None,
        description="Originator API URL for production"
    )

    KEY_ORIGINADOR_PROD: str | None = Field(
        default=None,
        description="Originator API key for production"
    )

    API_MAXIKASH_PROD: str | None = Field(
        default=None,
        description="Maxikash API URL for production"
    )

    URL_DATA_MAXI_PROD: str | None = Field(
        default=None,
        description="Data Maxi URL for production"
    )

    USRNAME_DATA_MAXI_PROD: str | None = Field(
        default=None,
        description="Data Maxi username for production"
    )

    PASSWORD_DATA_MAXI_PROD: str | None = Field(
        default=None,
        description="Data Maxi password for production"
    )

    AGENT_CHAT_URL_PROD: str | None = Field(
        default=None,
        description="Agent chat URL for production"
    )

    URL_CREDITOS_MAXI_PROD: str | None = Field(
        default=None,
        description="Creditos Maxi URL for production"
    )

    USRNAME_CREDITOS_MAXI_PROD: str | None = Field(
        default=None,
        description="Creditos Maxi username for production"
    )

    PASSWORD_CREDITOS_MAXI_PROD: str | None = Field(
        default=None,
        description="Creditos Maxi password for production"
    )

    # ==================== Computed Properties ====================

    @computed_field
    @property
    def IS_LOCAL(self) -> bool:
        """
        Detect if running in local environment.

        Returns:
            True if running locally (CLOUD_VAR is not set)
            False if running in Cloud Run (CLOUD_VAR is set)
        """
        return self.CLOUD_VAR is None

    @computed_field
    @property
    def IS_NOT_LOCAL(self) -> bool:
        """
        Detect if running in cloud environment (opposite of IS_LOCAL).

        Returns:
            True if running in Cloud Run
            False if running locally
        """
        return not self.IS_LOCAL

    @computed_field
    @property
    def URL_CALCULADORA(self) -> str | None:
        """Get the appropriate calculator URL based on environment."""
        return self.URL_CALCULADORA_PROD if self.ENV == "prod" else self.URL_CALCULADORA_DEV

    @computed_field
    @property
    def KEY_CALCULADORA(self) -> str | None:
        """Get the appropriate calculator key based on environment."""
        return self.KEY_CALCULADORA_PROD if self.ENV == "prod" else self.KEY_CALCULADORA_DEV

    @computed_field
    @property
    def URL_ORIGINADOR(self) -> str | None:
        """Get the appropriate originator URL based on environment."""
        return self.URL_ORIGINADOR_PROD if self.ENV == "prod" else self.URL_ORIGINADOR_DEV

    @computed_field
    @property
    def KEY_ORIGINADOR(self) -> str | None:
        """Get the appropriate originator key based on environment."""
        return self.KEY_ORIGINADOR_PROD if self.ENV == "prod" else self.KEY_ORIGINADOR_DEV

    @computed_field
    @property
    def API_MAXIKASH(self) -> str | None:
        """Get the appropriate Maxikash API URL based on environment."""
        return self.API_MAXIKASH_PROD if self.ENV == "prod" else self.API_MAXIKASH_DEV

    @computed_field
    @property
    def URL_DATA_MAXI(self) -> str | None:
        """Get the appropriate Data Maxi URL based on environment."""
        return self.URL_DATA_MAXI_PROD if self.ENV == "prod" else self.URL_DATA_MAXI_DEV

    @computed_field
    @property
    def USRNAME_DATA_MAXI(self) -> str | None:
        """Get the appropriate Data Maxi username based on environment."""
        return self.USRNAME_DATA_MAXI_PROD if self.ENV == "prod" else self.USRNAME_DATA_MAXI_DEV

    @computed_field
    @property
    def PASSWORD_DATA_MAXI(self) -> str | None:
        """Get the appropriate Data Maxi password based on environment."""
        return self.PASSWORD_DATA_MAXI_PROD if self.ENV == "prod" else self.PASSWORD_DATA_MAXI_DEV

    @computed_field
    @property
    def AGENT_CHAT_URL(self) -> str | None:
        """Get the appropriate agent chat URL based on environment."""
        return self.AGENT_CHAT_URL_PROD if self.ENV == "prod" else self.AGENT_CHAT_URL_DEV

    @computed_field
    @property
    def URL_CREDITOS_MAXI(self) -> str | None:
        """Get the appropriate Creditos Maxi URL based on environment."""
        return self.URL_CREDITOS_MAXI_PROD if self.ENV == "prod" else self.URL_CREDITOS_MAXI_DEV

    @computed_field
    @property
    def USRNAME_CREDITOS_MAXI(self) -> str | None:
        """Get the appropriate Creditos Maxi username based on environment."""
        return self.USRNAME_CREDITOS_MAXI_PROD if self.ENV == "prod" else self.USRNAME_CREDITOS_MAXI_DEV

    @computed_field
    @property
    def PASSWORD_CREDITOS_MAXI(self) -> str | None:
        """Get the appropriate Creditos Maxi password based on environment."""
        return self.PASSWORD_CREDITOS_MAXI_PROD if self.ENV == "prod" else self.PASSWORD_CREDITOS_MAXI_DEV

    # Backwards compatibility aliases
    @computed_field
    @property
    def PROJECT_ID(self) -> str | None:
        """Alias for GOOGLE_CLOUD_PROJECT for backwards compatibility."""
        return self.GOOGLE_CLOUD_PROJECT

    @computed_field
    @property
    def LOCATION(self) -> str:
        """Alias for GOOGLE_CLOUD_LOCATION for backwards compatibility."""
        return self.GOOGLE_CLOUD_LOCATION


# ==================== Singleton Instance ====================
# Create single instance to be imported throughout the application
settings = Settings()

# Log configuration on load
print(f"🔧 Configuration loaded:")
print(f"   └─ Environment: {settings.ENV}")
print(f"   └─ Log Level: {settings.EFFECTIVE_LOG_LEVEL}")
print(f"   └─ Location: {'Local' if settings.IS_LOCAL else 'Cloud Run'}")
print(f"   └─ Project ID: {settings.GOOGLE_CLOUD_PROJECT or 'Not set'}")
print(f"   └─ Cloud Location: {settings.GOOGLE_CLOUD_LOCATION}")
print(f"   └─ Agent Engine ID: {settings.AGENT_ENGINE_ID or 'Not set'}")
print(f"   └─ Root Agent Model: {settings.ROOT_AGENT_MODEL or 'Not set'}")

# Validate critical configurations
critical_configs = {
    'PROJECT_ID': settings.PROJECT_ID,
    'LOCATION': settings.LOCATION,
    'ROOT_AGENT_MODEL': settings.ROOT_AGENT_MODEL,
}

missing_configs = [key for key, value in critical_configs.items() if not value]
if missing_configs:
    print(f"⚠️  Missing critical configurations: {', '.join(missing_configs)}")

# Log environment-specific configuration
if settings.ENV == 'dev':
    print(f"   └─ Dev Config - URL_CALCULADORA: {settings.URL_CALCULADORA}")
    print(f"   └─ Dev Config - URL_ORIGINADOR: {settings.URL_ORIGINADOR}")
elif settings.ENV == 'prod':
    print(f"   └─ Prod Config - URL_CALCULADORA: {settings.URL_CALCULADORA}")
    print(f"   └─ Prod Config - URL_ORIGINADOR: {settings.URL_ORIGINADOR}")
