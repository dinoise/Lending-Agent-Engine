from .prompts import CatalogPrompts
from .tools import CatalogTools
from ...core import settings

from google.adk.agents import Agent
from google.genai import types

prompts = CatalogPrompts()
tools = CatalogTools()

catalog_agent = Agent(
    model=settings.ROOT_AGENT_MODEL,
    name='catalog_agent',
    instruction=prompts.get_full_prompt(),
    tools=tools.get_all_tools(),
    generate_content_config=types.GenerateContentConfig(temperature=0.03)
)