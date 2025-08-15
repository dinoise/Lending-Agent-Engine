import vertexai
from vertexai import agent_engines
from vertexai.preview.reasoning_engines import AdkApp
from maxiagent.agent import root_agent
import logging
import os
from dotenv import set_key

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION")
STAGING_BUCKET = os.getenv("STAGING_BUCKET")
# Define the path to the .env file relative to this script
ENV_FILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))

vertexai.init(
    project=GOOGLE_CLOUD_PROJECT,
    location=GOOGLE_CLOUD_LOCATION,
    staging_bucket=STAGING_BUCKET,
)

# Function to update the .env file
def update_env_file(agent_engine_id, env_file_path):
    """Updates the .env file with the agent engine ID."""
    try:
        set_key(env_file_path, "AGENT_ENGINE_ID", agent_engine_id)
        print(f"Updated AGENT_ENGINE_ID in {env_file_path} to {agent_engine_id}")
    except Exception as e:
        print(f"Error updating .env file: {e}")

logger.info("deploying app...")
app = AdkApp(
    agent=root_agent,
    enable_tracing=True,
)

def load_env_to_dict(filepath):
    env_dict = {}
    try:
        with open(filepath, 'r') as file:
            for line in file:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    if key in ["GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION"]: continue
                    env_dict[key.strip()] = value.strip().strip('"\'')
    except FileNotFoundError:
        print(f"Archivo {filepath} no encontrado")
    return env_dict


env_dict = load_env_to_dict(ENV_FILE_PATH)
print(env_dict)

logging.debug("deploying agent to agent engine:")

remote_app: agent_engines.AgentEngine = agent_engines.create(
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
    extra_packages=[
        "./maxiagent",
    ],
)

# log remote_app
logging.info(f"Deployed agent to Vertex AI Agent Engine successfully, resource name: {remote_app.resource_name}")

# Update the .env file with the new Agent Engine ID
update_env_file(remote_app.resource_name, ENV_FILE_PATH)