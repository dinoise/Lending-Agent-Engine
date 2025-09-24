from .prompts import ImageAnalysisPrompts
from .tools import ImageAnalysisTools
from ...config import current_config
from google.genai import types

from google.adk.agents import Agent

prompts = ImageAnalysisPrompts()
tools = ImageAnalysisTools()

image_analysis_agent = Agent(
    model=current_config.ROOT_AGENT_MODEL,
    name='image_analysis_agent',
    description='Especialista en análisis y clasificación de imágenes de documentos INE/IFE mexicanos',
    instruction=prompts.get_full_prompt(),
    tools=tools.get_all_tools(),
    generate_content_config=types.GenerateContentConfig(temperature=0.01)
)