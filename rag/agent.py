import os

from google.adk.agents import Agent

from dotenv import load_dotenv
from .prompts import return_instructions_root
from .tools import ask_vertex_retrieval

load_dotenv()

root_agent = Agent(
    model=os.environ.get("MODEL"),
    name='ask_rag_agent',
    instruction=return_instructions_root(),
    tools=[
        ask_vertex_retrieval,
    ]
)
