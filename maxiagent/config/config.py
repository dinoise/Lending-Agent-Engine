from os import getenv
from typing import Type, Union
import logging

# Configurar logging
logger = logging.getLogger(__name__)

class Config:
    """Configuraciones comunes"""
    FLASK_ENV: str = getenv("FLASK_ENV", "dev")
    PROJECT_ID: str | None = getenv("GOOGLE_CLOUD_PROJECT")
    LOCATION: str | None = getenv("GOOGLE_CLOUD_LOCATION")

    AGENT_ENGINE_ID: str | None = getenv("AGENT_ENGINE_ID")

    ROOT_AGENT_MODEL: str | None = getenv("ROOT_AGENT_MODEL")

    RAG_CORPUS: str | None = getenv("RAG_CORPUS")

    GOOGLE_SEARCH_API_KEY: str | None = getenv("GOOGLE_SEARCH_API_KEY")

    GOOGLE_CSE_ID: str | None = getenv("GOOGLE_CSE_ID")

    EMBEDDING_MODEL_NAME: str | None = getenv("EMBEDDING_MODEL_NAME")

    ADK_ARTIFACT_BUCKET: str | None = getenv("ADK_ARTIFACT_BUCKET")

class DevelopmentConfig(Config):
    """Configurations for development"""

    # Dectect if we are in local (CLOUD_VAR is a variable defined in Cloud Run)
    IS_NOT_LOCAL: bool = getenv("CLOUD_VAR") is not None

    URL_CALCULADORA: str | None = getenv("URL_CALCULADORA_DEV")
    KEY_CALCULADORA: str | None = getenv("KEY_CALCULADORA_DEV")

    URL_ORIGINADOR: str | None = getenv("URL_ORIGINADOR_DEV")
    KEY_ORIGINADOR: str | None = getenv("KEY_ORIGINADOR_DEV")

    API_MAXIKASH: str | None = getenv("API_MAXIKASH_DEV")

    URL_DATA_MAXI: str | None = getenv("URL_DATA_MAXI_DEV")
    USRNAME_DATA_MAXI: str | None = getenv("USRNAME_DATA_MAXI_DEV")
    PASSWORD_DATA_MAXI: str | None = getenv("PASSWORD_DATA_MAXI_DEV")

    # Configuration for PostgreSQL
    PG_HOST = "POSTGRE_IP_PRIVATE" if IS_NOT_LOCAL else "POSTGRE_IP_PUBLIC"
    PG_PORT = "POSTGRE_PORT"
    PG_USER = "POSTGRE_USR_RAG_REPO_DEV"
    PG_PASSWORD = "POSTGRE_PASS_RAG_REPO_DEV"
    PG_NAME = "POSTGRE_DB_RAG_REPO"

class ProductionConfig(Config):
    """Configurations for production"""

    URL_CALCULADORA: str | None = getenv("URL_CALCULADORA_PROD")
    KEY_CALCULADORA: str | None = getenv("KEY_CALCULADORA_PROD")

    URL_ORIGINADOR: str | None = getenv("URL_ORIGINADOR_PROD")
    KEY_ORIGINADOR: str | None = getenv("KEY_ORIGINADOR_PROD")

    API_MAXIKASH: str | None = getenv("API_MAXIKASH_PROD")

    URL_DATA_MAXI: str | None = getenv("URL_DATA_MAXI_PROD")
    USRNAME_DATA_MAXI: str | None = getenv("USRNAME_DATA_MAXI_PROD")
    PASSWORD_DATA_MAXI: str | None = getenv("PASSWORD_DATA_MAXI_PROD")

    # Configuration for PostgreSQL
    PG_HOST = "POSTGRE_IP_PRIVATE"
    PG_PORT = "POSTGRE_PORT"
    PG_USER = "POSTGRE_USR_RAG_REPO_PROD"
    PG_PASSWORD = "POSTGRE_PASS_RAG_REPO_PROD"
    PG_NAME = "POSTGRE_DB_RAG_REPO"

ConfigType = Union[Type[DevelopmentConfig], Type[ProductionConfig]]

# Dictionary con tipo explícito
config_by_name: dict[str, ConfigType] = {
    'dev': DevelopmentConfig,
    'prod': ProductionConfig
}

# Uso con tipo definido
config_name: str | None = getenv("ENV")
current_config: ConfigType = config_by_name[config_name if config_name is not None else 'dev']

# Logging de configuración para debugging
logger.info(f"🔧 Config loaded: ENV={config_name or 'dev (default)'}")
logger.info(f"🔧 Config type: {current_config.__name__}")
logger.info(f"🔧 PROJECT_ID: {current_config.PROJECT_ID}")
logger.info(f"🔧 ROOT_AGENT_MODEL: {current_config.ROOT_AGENT_MODEL}")

# Validar configuraciones críticas
critical_configs = {
    'PROJECT_ID': current_config.PROJECT_ID,
    'LOCATION': current_config.LOCATION,
    'ROOT_AGENT_MODEL': current_config.ROOT_AGENT_MODEL,
}

missing_configs = [key for key, value in critical_configs.items() if not value]
if missing_configs:
    logger.warning(f"⚠️  Missing critical configurations: {', '.join(missing_configs)}")

# Logging específico por ambiente
if config_name == 'dev' or not config_name:
    logger.info(f"🔧 Dev Config - URL_CALCULADORA: {current_config.URL_CALCULADORA}")
    logger.info(f"🔧 Dev Config - URL_ORIGINADOR: {current_config.URL_ORIGINADOR}")
elif config_name == 'prod':
    logger.info(f"🔧 Prod Config - URL_CALCULADORA: {current_config.URL_CALCULADORA}")
    logger.info(f"🔧 Prod Config - URL_ORIGINADOR: {current_config.URL_ORIGINADOR}")