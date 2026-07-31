"""
sitecustomize.py - Configuración automática para Python

Este archivo se ejecuta automáticamente cuando Python inicia.
Se usa para configurar el logging antes de que cualquier otro código se ejecute.
"""

import logging

# Suprimir warnings informativos de Google Gen AI SDK
# Estos warnings son generados por el ADK framework cuando procesa respuestas
# que incluyen thought_signature y function_call, lo cual es normal
logging.getLogger('google.genai.types').setLevel(logging.ERROR)
