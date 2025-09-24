from .prompts import OriginationPrompts
from .tools import OriginationTools
from ...config import current_config
from google.genai import types

from google.adk.agents import Agent

from ..image_analysis_agent import image_analysis_agent

prompts = OriginationPrompts()
tools = OriginationTools()

origination_agent = Agent(
    model=current_config.ROOT_AGENT_MODEL,
    name='origination_agent',
    instruction=prompts.get_full_prompt(),
    tools=tools.get_all_tools(),
    sub_agents=[image_analysis_agent],
    generate_content_config=types.GenerateContentConfig(temperature=0.07)
)
