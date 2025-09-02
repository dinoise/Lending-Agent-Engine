from . import current_config
from .prompts import return_instructions_root
from .tools import (rag_response, 
                    google_web_search,
                    calculate_quotation,
                    save_ingreso_mensual,
                    save_precio_moto,
                    save_fecha_nacimiento,
                    save_marca_moto,
                    save_modelo_moto,
                    check_quotation_status)

from google.adk.agents import Agent

root_agent = Agent(
    model=current_config.ROOT_AGENT_MODEL,
    name='maxiagent',
    instruction=return_instructions_root(),
    tools=[
        rag_response,
        google_web_search,
        calculate_quotation,
        save_ingreso_mensual,
        save_precio_moto,
        save_fecha_nacimiento,
        save_marca_moto,
        save_modelo_moto,
        check_quotation_status
    ]
)