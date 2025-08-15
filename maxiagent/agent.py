import os

from google.adk.agents import Agent

from dotenv import load_dotenv
from .prompts import return_instructions_root
from .tools import (rag_response, 
                    google_web_search)

load_dotenv()

root_agent = Agent(
    model=os.environ.get("MODEL"),
    name='maxiagent',
    instruction=return_instructions_root(),
    tools=[
        rag_response,
        google_web_search
    ]
)
