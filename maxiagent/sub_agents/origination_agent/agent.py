from .prompts import OriginationPrompts
from .tools import OriginationTools
from ...config import current_config
from google.genai import types

from google.adk.agents import Agent

from google.adk.sessions import InMemorySessionService
from google.adk.artifacts import InMemoryArtifactService  # Servicio de artifacts en memoria
from google.adk.runners import Runner

session_service = InMemorySessionService()
artifact_service = InMemoryArtifactService()

prompts = OriginationPrompts()
tools = OriginationTools()

origination_agent = Agent(
    model=current_config.ROOT_AGENT_MODEL,
    name='origination_agent',
    instruction=prompts.get_full_prompt(),
    tools=tools.get_all_tools(),
    generate_content_config=types.GenerateContentConfig(temperature=0.07)
)

runner = Runner(
    agent=origination_agent,
    app_name="app_origination",
    session_service=session_service,
    artifact_service=artifact_service
)