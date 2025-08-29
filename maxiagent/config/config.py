from os import getenv
from dotenv import load_dotenv

load_dotenv()  # take environment variables

class Config:
    """Configuraciones comunes"""
    FLASK_ENV: str = getenv("FLASK_ENV", "dev")
    PROJECT_ID: str | None = getenv("GOOGLE_CLOUD_PROJECT")

    AGENT_ENGINE_ID: str | None = getenv("AGENT_ENGINE_ID")

    ROOT_AGENT_MODEL: str | None = getenv("ROOT_AGENT_MODEL")

    RAG_CORPUS: str | None = getenv("RAG_CORPUS")

    GOOGLE_SEARCH_API_KEY: str | None = getenv("GOOGLE_SEARCH_API_KEY")

    GOOGLE_CSE_ID: str | None = getenv("GOOGLE_CSE_ID")

class DevelopmentConfig(Config):
    """Configurations for development"""

    # Dectect if we are in local (CLOUD_VAR is a variable defined in Cloud Run)
    IS_NOT_LOCAL: bool = getenv("CLOUD_VAR") is not None

    URL_CALCULADORA: str | None = getenv("URL_CALCULADORA_DEV")
    KEY_CALCULADORA: str | None = getenv("KEY_CALCULADORA_DEV")

class ProductionConfig(Config):
    """Configurations for production"""

    URL_CALCULADORA: str | None = getenv("URL_CALCULADORA_PROD")
    KEY_CALCULADORA: str | None = getenv("KEY_CALCULADORA_PROD")

# Dictionary to select the environment
config_by_name = {
    'dev': DevelopmentConfig,
    'prod': ProductionConfig
}