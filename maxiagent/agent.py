from .prompts import RootAgentPrompts
from .tools import RootAgentTools
from .config import current_config

# Import sub-agents
from .sub_agents import (credit_advice_agent,
                        calculation_agent,
                        catalog_agent)

from google.adk.agents import Agent

prompts = RootAgentPrompts()
tools = RootAgentTools()

root_agent = Agent(
    model=current_config.ROOT_AGENT_MODEL,
    name='maxiagent',
    instruction=prompts.get_coordination_prompt(),
    sub_agents=[credit_advice_agent,
                calculation_agent,
                catalog_agent]
)