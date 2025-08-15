from . import current_config

from .prompts import return_instructions_root
from .tools import (rag_response, 
                    google_web_search)

from google.adk.agents import Agent

root_agent = Agent(
    model=current_config.ROOT_AGENT_MODEL,
    name='maxiagent',
    instruction=return_instructions_root(),
    tools=[
        rag_response,
        google_web_search
    ]
)
