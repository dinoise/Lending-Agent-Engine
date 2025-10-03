"""
MaxiAgent - Sistema de agentes inteligentes para Maxikash

Este módulo inicializa el sistema de agentes y configura el logging.
"""

import logging

# Suprimir warnings informativos de Google Gen AI SDK
# Estos warnings son generados por el ADK framework cuando procesa respuestas
# que incluyen thought_signature y function_call, lo cual es normal en el flujo
# de ejecución de los agentes. El framework maneja estos parts correctamente.
logging.getLogger('google.genai.types').setLevel(logging.ERROR)

# Exportar el agente raíz
from .agent import root_agent

__all__ = ['root_agent']
