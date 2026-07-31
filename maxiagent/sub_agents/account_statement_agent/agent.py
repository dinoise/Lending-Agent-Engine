from .prompts import AccountStatementPrompts
from .tools import AccountStatementTools
from ...core import settings

from google.adk.agents import Agent
from google.genai import types

prompts = AccountStatementPrompts()
tools = AccountStatementTools()

account_statement_agent = Agent(
    model=settings.ROOT_AGENT_MODEL,
    name='account_statement_agent',
    instruction=prompts.get_full_prompt(),
    tools=tools.get_all_tools(),
    generate_content_config=types.GenerateContentConfig(
        temperature=0.03,
        max_output_tokens=512  # Respuestas cortas: tabla de estado de cuenta
    )
)