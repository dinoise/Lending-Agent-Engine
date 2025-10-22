import logging

# Suprimir warnings informativos de Google Gen AI SDK (por si acaso)
# Este logger ya debería estar configurado en __init__.py, pero lo reforzamos aquí
logging.getLogger('google.genai.types').setLevel(logging.ERROR)

from .prompts import RootAgentPrompts
from .tools import RootAgentTools
from .core import settings

# Import sub-agents
from .sub_agents import (credit_advice_agent,
                        catalog_agent,
                        origination_agent,
                        account_statement_agent)

from google.adk.agents import Agent
from google.genai import types

prompts = RootAgentPrompts()
tools = RootAgentTools()

root_agent = Agent(
    model=settings.ROOT_AGENT_MODEL,
    name='maxiagent',
    instruction=prompts.get_full_prompt(),
    global_instruction=prompts.get_global_instruction(),
    sub_agents=[credit_advice_agent,
                catalog_agent,
                origination_agent,
                account_statement_agent],
    generate_content_config=types.GenerateContentConfig(temperature=0.05)
)