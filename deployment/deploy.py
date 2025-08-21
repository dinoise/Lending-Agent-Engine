import vertexai
from vertexai import agent_engines
from vertexai.preview.reasoning_engines import AdkApp
from maxiagent.agent import root_agent
import logging
import os
from dotenv import set_key
import argparse

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Deploy Agent to Vertex AI Agent Engine')
    parser.add_argument('--create', action='store_true', help='Create a new agent')
    parser.add_argument('--update', action='store_true', help='Update an existing agent')
    parser.add_argument('--resource-id', type=str, help='Resource ID of the agent to update')
    return parser.parse_args()

def update_env_file(agent_engine_id, env_file_path):
    """Updates the .env file with the agent engine ID."""
    try:
        set_key(env_file_path, "AGENT_ENGINE_ID", agent_engine_id)
        print(f"Updated AGENT_ENGINE_ID in {env_file_path} to {agent_engine_id}")
    except Exception as e:
        print(f"Error updating .env file: {e}")

def load_env_to_dict(filepath):
    env_dict = {}
    try:
        with open(filepath, 'r') as file:
            for line in file:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    if key in ["GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION"]: 
                        continue
                    env_dict[key.strip()] = value.strip().strip('"\'')
    except FileNotFoundError:
        print(f"Archivo {filepath} no encontrado")
    return env_dict

def deploy_agent(args):
    # Configuración inicial
    GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
    GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION")
    STAGING_BUCKET = os.getenv("STAGING_BUCKET")
    ENV_FILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))

    vertexai.init(
        project=GOOGLE_CLOUD_PROJECT,
        location=GOOGLE_CLOUD_LOCATION,
        staging_bucket=STAGING_BUCKET,
    )

    # Cargar variables de entorno
    env_dict = load_env_to_dict(ENV_FILE_PATH)
    print(env_dict)

    # Crear la aplicación ADK
    logger.info("Creating ADK app...")
    app = AdkApp(
        agent=root_agent,
        enable_tracing=True,
    )

    if args.create:
        # Crear nuevo agente
        logger.info("Deploying new agent to Agent Engine...")
        remote_app = agent_engines.create(
            app,
            env_vars=env_dict,
            requirements=[
                "google-cloud-aiplatform[adk,agent-engines]",
                "google-adk",
                "python-dotenv",
                "google-auth",
                "tqdm",
                "requests",
                "deprecated",
                "llama_index"
            ],
            extra_packages=["./maxiagent"],
        )
        
        logger.info(f"Deployed agent to Vertex AI Agent Engine successfully, resource name: {remote_app.resource_name}")
        update_env_file(remote_app.resource_name, ENV_FILE_PATH)
        
    elif args.update and args.resource_id:
        # Actualizar agente existente
        logger.info(f"Updating existing agent: {args.resource_id}")
        remote_app = agent_engines.update(
            resource_name=args.resource_id,
            agent_engine=app,
            env_vars=env_dict,
            requirements=[
                "google-cloud-aiplatform[adk,agent-engines]",
                "google-adk",
                "python-dotenv",
                "google-auth",
                "tqdm",
                "requests",
                "deprecated",
                "llama_index"
            ],
            extra_packages=["./maxiagent"],
        )
        
        logger.info(f"Successfully updated agent: {args.resource_id}")
    else:
        logger.error("Invalid arguments. Use --create to create new agent or --update with --resource-id to update existing agent.")

if __name__ == "__main__":
    args = parse_arguments()
    deploy_agent(args)