from .prompts import CatalogPrompts
from .tools import CatalogTools
from ...config import current_config

from google.adk.agents import Agent
from google.genai import types

prompts = CatalogPrompts()
tools = CatalogTools()

catalog_agent = Agent(
    model=current_config.ROOT_AGENT_MODEL,
    name='catalog_agent',
    instruction=prompts.get_full_prompt(),
    tools=tools.get_all_tools(),
    generate_content_config=types.GenerateContentConfig(temperature=0.03)
)