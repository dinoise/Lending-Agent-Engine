import vertexai
import argparse
import sys
import os
import logging
from dotenv import load_dotenv, set_key, find_dotenv

from typing import Dict
from dataclasses import dataclass
from vertexai.preview.reasoning_engines import AdkApp
from google.api_core import exceptions as google_exceptions

# ⚠️ CRÍTICO: Cargar variables de entorno ANTES de importar el agente
# Esto asegura que current_config tenga valores cuando se inicialicen los agentes
load_dotenv()

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Ahora sí importar el agente (después de cargar .env)
from maxiagent.agent import root_agent

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
    # Nota: Sin especificar versión usa la última disponible
    # Para versiones específicas usar formato: "package>=1.0.0" o "package==1.0.0"
    BASE_REQUIREMENTS: list[str] = [
        "google-cloud-aiplatform[adk,agent_engines]>=1.118.0",  # Última versión con extras para Agent Engine
        "google-adk>=1.15.1",  # Version sin bug
        "python-dotenv",  # Para manejo de variables de entorno
        "google-auth",  # Autenticación de Google Cloud
        "tqdm",  # Barras de progreso
        "requests",  # Cliente HTTP
        "deprecated",  # Decoradores de deprecación
        "llama_index",  # Framework de LLM
        "langchain-google-vertexai",  # Integración LangChain-Vertex
        "beautifulsoup4",  # Parser HTML (usado en get_page_content)
    ]
    
    def __init__(self, config: AgentConfig) -> None:
        self.config: AgentConfig = config
        self.client: vertexai.Client = self._initialize_vertex_client()
        self.env_vars: Dict[str, str] = self._load_env_vars()

    def _initialize_vertex_client(self) -> vertexai.Client:
        """Inicializa el cliente de Vertex AI (nueva API basada en cliente)"""
        logger.info(f"🔧 Initializing Vertex AI Client with project={self.config.project}, location={self.config.location}")
        return vertexai.Client(
            project=self.config.project,
            location=self.config.location,
        )
    
    def _load_env_vars(self) -> Dict[str, str]:
        """Carga variables de entorno desde archivo"""
        env_dict = {}

        # Definir required_vars basado en el ambiente
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
                "PASSWORD_DATA_MAXI_PROD",
                "ADK_ARTIFACT_BUCKET"
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
                "PASSWORD_DATA_MAXI_DEV",
                "ADK_ARTIFACT_BUCKET"
            ]

        # Intentar cargar desde archivo .env
        try:
            with open(self.config.env_file_path, 'r') as file:
                for line in file:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        if key in ["GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION"]: continue
                        env_dict[key.strip()] = value.strip().strip('"\'')
            logger.info(f"📄 Loaded env vars from file: {self.config.env_file_path}")
        except FileNotFoundError:
            logger.warning(f"📄 Archivo {self.config.env_file_path} no encontrado")
            logger.info(f"📦 Loading env vars from os.environ (CI/CD mode)")

            # En CI/CD, cargar desde os.environ
            for var_name in required_vars:
                if var_name in os.environ:
                    env_dict[var_name] = os.environ[var_name]
                    logger.debug(f"✓ Loaded env var: {var_name}")
                else:
                    logger.warning(f"⚠️  Variable de entorno requerida no encontrada: {var_name}")

        logger.info(f"📦 ENV VARS loaded: {list(env_dict.keys())}")
        logger.info(f"📦 Total ENV VARS: {len(env_dict)}/{len(required_vars)}")

        # Validación crítica
        if len(env_dict) < len(required_vars):
            missing = set(required_vars) - set(env_dict.keys())
            logger.error(f"❌ Missing {len(missing)} required env vars: {missing}")

        # Log de validación de variables críticas
        critical_vars = ['ENV', 'ROOT_AGENT_MODEL', 'GOOGLE_CLOUD_PROJECT']
        for var in critical_vars:
            if var in env_dict:
                logger.info(f"✓ Critical var '{var}' = '{env_dict[var][:50]}...' " if len(env_dict[var]) > 50 else f"✓ Critical var '{var}' = '{env_dict[var]}'")
        return env_dict
    
    def _create_adk_app(self) -> AdkApp:
        """Crea la aplicación ADK"""
        logger.info("Creating ADK app...")
        return AdkApp(
            agent=root_agent,
            enable_tracing=True,
        )
    
    def create_agent(self, display_name: str) -> str:
        """Crea un nuevo agente usando la nueva API basada en cliente"""
        app = self._create_adk_app()

        logger.info(f"🚀 Creating agent with display_name: {display_name}")

        remote_app = self.client.agent_engines.create(
            agent=app,
            config={
                "staging_bucket": self.config.staging_bucket,
                "requirements": self.BASE_REQUIREMENTS,
                "display_name": display_name,
                "env_vars": self.env_vars,
                "extra_packages": ["./maxiagent"],
                "min_instances": 1,  # Mantener instancia caliente
                "max_instances": 10,  # Auto-scaling
            }
        )

        remote_name = remote_app.api_resource.name
        logger.info(f"✅ Agent creado exitosamente: {remote_name}")
        # self._update_env_file(remote_app.resource_name)
        return remote_name
    
    def update_agent(self, resource_id: str) -> str:
        """Actualiza un agente existente usando la nueva API basada en cliente"""
        app: AdkApp = self._create_adk_app()

        # Construir el nombre completo del recurso si solo se proporciona el ID
        if not resource_id.startswith("projects/"):
            resource_name: str = f"projects/{self.config.project}/locations/{self.config.location}/reasoningEngines/{resource_id}"
        else:
            resource_name: str = resource_id

        logger.info(f"🔄 Updating agent: {resource_name}")

        # Nota: staging_bucket, min_instances, max_instances NO son parámetros válidos en update
        remote_app = self.client.agent_engines.update(
            name=resource_name,
            agent=app,
            config={
                "staging_bucket": self.config.staging_bucket,
                "env_vars": self.env_vars,
                "requirements": self.BASE_REQUIREMENTS,
                "extra_packages": ["./maxiagent"],
                "min_instances": 1,
                "max_instances": 10
            }
        )

        logger.info(f"✅ Agent actualizado exitosamente: {resource_name}")
        return remote_app.api_resource.name
    
    def delete_agent(self, resource_id: str) -> None:
        """Elimina un agente usando la nueva API basada en cliente"""
        try:
            logger.info(f"🗑️  Deleting agent: {resource_id}")
            # En la nueva API, delete() se llama directamente con el name
            self.client.agent_engines.delete(
                name=resource_id,
                force=True  # Elimina incluso si tiene sesiones o memoria asociadas
            )
            logger.info(f"✅ Agent eliminado exitosamente: {resource_id}")
        except google_exceptions.NotFound:
            logger.error(f"❌ Agent no encontrado: {resource_id}")
            raise
        except Exception as e:
            logger.error(f"❌ Error eliminando agent {resource_id}: {e}")
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