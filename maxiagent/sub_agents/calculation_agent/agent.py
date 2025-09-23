from .prompts import CalculationPrompts
from .tools import CalculationTools
from ...config import current_config
from ..session_management_agent import session_management_agent

from google.adk.agents import Agent
from google.genai import types

prompts = CalculationPrompts()
tools = CalculationTools()

calculation_agent = Agent(
    model=current_config.ROOT_AGENT_MODEL,
    name='calculation_agent',
    instruction=prompts.get_full_prompt(),
    tools=tools.get_all_tools(),
    sub_agents=[session_management_agent],
    generate_content_config=types.GenerateContentConfig(temperature=0.01)
)