from .prompts import ImageAnalysisPrompts
from .tools import ImageAnalysisTools
from ...core import settings
from google.genai import types

from google.adk.agents import Agent

prompts = ImageAnalysisPrompts()
tools = ImageAnalysisTools()

image_analysis_agent = Agent(
    model=settings.ROOT_AGENT_MODEL,
    name='image_analysis_agent',
    description='Especialista en análisis y clasificación de imágenes de documentos INE/IFE mexicanos',
    instruction=prompts.get_full_prompt(),
    tools=tools.get_all_tools(),
    generate_content_config=types.GenerateContentConfig(
        temperature=0.01,
        max_output_tokens=256  # Respuestas muy cortas: clasificación de documentos (FRENTE/REVERSO)
    )
)