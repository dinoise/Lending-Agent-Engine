from .prompts import RootAgentPrompts
from .tools import RootAgentTools
from .config import current_config

from google.adk.agents import Agent

prompts = RootAgentPrompts()
tools = RootAgentTools()

root_agent = Agent(
    model=current_config.ROOT_AGENT_MODEL,
    name='maxiagent',
    instruction=prompts.get_full_prompt(),
    tools=tools.get_all_tools()
)