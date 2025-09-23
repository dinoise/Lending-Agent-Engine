from .prompts import CatalogPrompts
from .tools import CatalogTools
from ...config import current_config

from google.adk.agents import Agent

prompts = CatalogPrompts()
tools = CatalogTools()

catalog_agent = Agent(
    model=current_config.ROOT_AGENT_MODEL,
    name='catalog_agent',
    instruction=prompts.get_full_prompt(),
    tools=tools.get_all_tools()
)