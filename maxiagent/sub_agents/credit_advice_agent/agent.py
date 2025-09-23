from .prompts import CreditAdvicePrompts
from .tools import CreditAdviceTools
from ...config import current_config

from google.adk.agents import Agent
from google.genai import types

prompts = CreditAdvicePrompts()
tools = CreditAdviceTools()

credit_advice_agent = Agent(
    model=current_config.ROOT_AGENT_MODEL,
    name='credit_advice_agent',
    instruction=prompts.get_full_prompt(),
    tools=tools.get_all_tools(),
    generate_content_config=types.GenerateContentConfig(temperature=0.07)
)