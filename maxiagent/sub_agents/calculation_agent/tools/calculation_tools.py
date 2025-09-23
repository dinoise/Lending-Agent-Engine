import requests
import json

from datetime import datetime
from typing import List, Callable, Dict

from ....config import current_config

from google.adk.tools.tool_context import ToolContext

class CalculationTools:
    """Clase para gestionar las herramientas del agente de cálculo de cotizaciones."""

    def __init__(self):
        self._tools = {
            'calculation_tools': {
                'calculate_quotation': self.calculate_quotation
            }
        }

    def get_all_tools(self) -> List:
        """Retorna una lista con todas las funciones herramienta."""
        all_tools = []
        for category in self._tools.values():
            all_tools.extend(category.values())
        return all_tools

    def get_tools_by_category(self, category: str) -> Dict[str, Callable]:
        """Retorna las herramientas de una categoría específica."""
        return self._tools.get(category, {})

    def get_tool(self, tool_name: str) -> Callable:
        """Retorna una herramienta específica por nombre."""
        for category in self._tools.values():
            if tool_name in category:
                return category[tool_name]
        raise ValueError(f"Herramienta '{tool_name}' no encontrada")

    # --- Herramientas de Cálculo ---
    def calculate_quotation(self, tool_context: ToolContext) -> list:
        """Calcula ofertas de financiamiento usando los datos del estado de la sesión.

        Returns:
            Lista con las opciones de financiamiento calculadas
        """
        state = tool_context.state

        # Verificar que todos los datos estén presentes
        required_fields = ["ingreso_mensual", "precio_moto", "fecha_nacimiento", "marca_moto", "modelo_moto"]
        missing_fields = [field for field in required_fields if field not in state or not state[field]]

        if missing_fields:
            return [{"error": f"Datos faltantes: {', '.join(missing_fields)}"}]

        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Python-HTTP-Post-Client/1.0',
            'Authorization': current_config.KEY_CALCULADORA,
            'usuario': ''
        }

        data: dict = {
            "ingresoMensual": state["ingreso_mensual"],
            "precioMoto": state["precio_moto"],
            "garantia": None,
            "fechaNacimiento": state["fecha_nacimiento"],
            "idMunicipio": 1,
            "idEstado": 1,
            "codigoPostal": "06850",
            "idSucursal": 1,
            "idDistribuidor": 1,
            "marcaMoto": state["marca_moto"],
            "modeloMoto": state["modelo_moto"],
            "fechaHoraCreacionOferta": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "idUsuarioCreacion": "111",
            "idOferta": "111",
            "idPais": "MX"
        }

        try:
            response: requests.Response = requests.post(
                url=current_config.URL_CALCULADORA,
                json=data,
                headers=headers,
                timeout=30
            )

            print( f"responseee {response}" )

            response.raise_for_status()

            try:
                return response.json()["output"]["calculos"]
            except (json.JSONDecodeError, KeyError):
                return [{"error": "Error procesando la respuesta del servidor"}]

        except requests.exceptions.RequestException as e:
            return [{"error": f"Error de conexión: {str(e)}"}]