from .prompts import SessionManagementPrompts
from .tools import SessionManagementTools
from ...config import current_config

from google.adk.agents import Agent

prompts = SessionManagementPrompts()
tools = SessionManagementTools()

session_management_agent = Agent(
    model=current_config.ROOT_AGENT_MODEL,
    name='session_management_agent',
    instruction=prompts.get_full_prompt(),
    tools=tools.get_all_tools()
)