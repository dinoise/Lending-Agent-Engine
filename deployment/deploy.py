import vertexai
import argparse
import sys
import os
import logging

from typing import Dict
from dataclasses import dataclass
from vertexai import agent_engines
from vertexai.preview.reasoning_engines import AdkApp
from google.api_core import exceptions as google_exceptions
from dotenv import set_key, find_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from maxiagent.agent import root_agent

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@dataclass
class AgentConfig:
    project: str
    location: str
    staging_bucket: str
    env_file_path: str | None = None
    env: str = 'dev'

    def __post_init__(self):
        logger.info(f"USING ENV {self.env}")
        if not self.env_file_path:
            self.env_file_path = find_dotenv(usecwd=True)

class VertexAgentManager:
    """Manejador para operaciones de Agent Engines en Vertex AI"""
    
    # Paquetes requeridos estándar
    BASE_REQUIREMENTS: list[str] = [
        "google-cloud-aiplatform[adk,agent-engines]",
        "google-adk",
        "python-dotenv",
        "google-auth",
        "tqdm",
        "requests",
        "deprecated",
        "llama_index",
        "langchain-google-vertexai",
        "pgvector",
        "SQLAlchemy",
        "psycopg2-binary",
        "marshmallow_sqlalchemy"
    ]
    
    def __init__(self, config: AgentConfig) -> None:
        self.config: AgentConfig = config
        self._initialize_vertex()
        self.env_vars: Dict[str, str] = self._load_env_vars()
        
    def _initialize_vertex(self) -> None:
        """Inicializa el entorno de Vertex AI"""
        vertexai.init(
            project=self.config.project,
            location=self.config.location,
            staging_bucket=self.config.staging_bucket,
        )
    
    def _load_env_vars(self) -> Dict[str, str]:
        """Carga variables de entorno desde archivo"""
        env_dict = {}
        try:
            with open(self.config.env_file_path, 'r') as file:
                for line in file:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        if key in ["GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION"]: continue
                        env_dict[key.strip()] = value.strip().strip('"\'')
        except FileNotFoundError:
            logger.warning(f"Archivo {self.config.env_file_path} no encontrado")
            # En GitHub Actions, usar las variables ya disponibles en os.environ
            # pero filtrando solo las que necesitamos
            env: str = self.config.env

            if env == "prod":
                required_vars: list[str] = [
                    "ENV",
                    "AGENT_ENGINE_ID",
                    "STAGING_BUCKET",
                    "RAG_CORPUS",
                    "GOOGLE_CSE_ID",
                    "GOOGLE_SEARCH_API_KEY",
                    "ROOT_AGENT_MODEL",
                    "URL_CALCULADORA_PROD",
                    "KEY_CALCULADORA_PROD",
                    "API_MAXIKASH_PROD",
                    "URL_ORIGINADOR_PROD",
                    "KEY_ORIGINADOR_PROD",
                    "URL_DATA_MAXI_PROD",
                    "USRNAME_DATA_MAXI_PROD",
                    "PASSWORD_DATA_MAXI_PROD"
                ]
            else:
                required_vars: list[str] = [
                    "ENV",
                    "AGENT_ENGINE_ID",
                    "STAGING_BUCKET",
                    "RAG_CORPUS",
                    "GOOGLE_CSE_ID",
                    "GOOGLE_SEARCH_API_KEY",
                    "ROOT_AGENT_MODEL",
                    "URL_CALCULADORA_DEV",
                    "KEY_CALCULADORA_DEV",
                    "API_MAXIKASH_DEV",
                    "URL_ORIGINADOR_DEV",
                    "KEY_ORIGINADOR_DEV",
                    "URL_DATA_MAXI_DEV",
                    "USRNAME_DATA_MAXI_DEV",
                    "PASSWORD_DATA_MAXI_DEV"
                ]
            
            for var_name in required_vars:
                if var_name in os.environ:
                    env_dict[var_name] = os.environ[var_name]
                else:
                    logger.warning(f"Variable de entorno requerida no encontrada: {var_name}")
                    
        logger.info(f"ENV VARS {env_dict}.")
        logger.info(f"Len of ENV VARS {len(env_dict)}")
        return env_dict
    
    def _create_adk_app(self) -> AdkApp:
        """Crea la aplicación ADK"""
        logger.info("Creating ADK app...")
        return AdkApp(
            agent=root_agent,
            enable_tracing=True,
        )
    
    def create_agent(self, display_name: str) -> str:
        """Crea un nuevo agente"""
        app = self._create_adk_app()
        
        remote_app = agent_engines.create(
            agent_engine=app,
            requirements=self.BASE_REQUIREMENTS,
            display_name=display_name,
            env_vars=self.env_vars,
            extra_packages=["./maxiagent"],
        )
        
        logger.info(f"Agent creado: {remote_app.resource_name}")
        # self._update_env_file(remote_app.resource_name)
        return remote_app.resource_name
    
    def update_agent(self, resource_id: str) -> str:
        """Actualiza un agente existente"""
        app = self._create_adk_app()
        
        remote_app = agent_engines.update(
            resource_name=resource_id,
            agent_engine=app,
            env_vars=self.env_vars,
            requirements=self.BASE_REQUIREMENTS,
            extra_packages=["./maxiagent"],
        )
        
        logger.info(f"Agent actualizado: {resource_id}")
        return remote_app.resource_name
    
    def delete_agent(self, resource_id: str) -> None:
        """Elimina un agente"""
        try:
            remote_agent = agent_engines.get(resource_id)
            remote_agent.delete(force=True)
            logger.info(f"Agent eliminado: {resource_id}")
        except google_exceptions.NotFound:
            logger.error(f"Agent no encontrado: {resource_id}")
            raise
        except Exception as e:
            logger.error(f"Error eliminando agent {resource_id}: {e}")
            raise
    
    def _update_env_file(self, agent_engine_id: str) -> None:
        """Actualiza el archivo .env con el ID del agent engine"""
        try:
            set_key(self.config.env_file_path, "AGENT_ENGINE_ID", agent_engine_id)
            logger.info(f"Actualizado AGENT_ENGINE_ID en {self.config.env_file_path}")
        except Exception as e:
            logger.error(f"Error actualizando .env file: {e}")
            raise

def main() -> None:
    parser = argparse.ArgumentParser(description='Manage Vertex AI Agent Engines')
    parser.add_argument('--create', action='store_true', help='Create a new agent')
    parser.add_argument('--display-name', type=str, help='Display name for the agent')
    parser.add_argument('--delete', action='store_true', help='Delete an agent')
    parser.add_argument('--update', action='store_true', help='Update an agent')
    parser.add_argument('--resource-id', type=str, help='Agent resource ID')
    parser.add_argument('--env', type=str, help='Environment (dev or prod)')
    
    args: argparse.Namespace = parser.parse_args()
    
    # Configuración desde variables de entorno
    config = AgentConfig(
        project=os.getenv("GOOGLE_CLOUD_PROJECT"),
        location=os.getenv("GOOGLE_CLOUD_LOCATION"),
        staging_bucket=os.getenv("STAGING_BUCKET"),
        env=args.env
    )
    
    manager = VertexAgentManager(config)
    
    try:
        if args.create and args.display_name and args.env:
            manager.create_agent(args.display_name)
        elif args.update and args.resource_id and args.env:
            manager.update_agent(args.resource_id)
        elif args.delete and args.resource_id:
            manager.delete_agent(args.resource_id)
        else:
            logger.error("Comando no válido. Verifica los argumentos.")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Operación fallida: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()