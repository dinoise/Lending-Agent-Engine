import requests
import json

from datetime import datetime
from typing import Any, Dict

from ..config import current_config
from ..utils import get_page_content
from .base_tools import BaseAgentTools

from googleapiclient.discovery import build
from google.adk.tools.tool_context import ToolContext


class RootAgentTools(BaseAgentTools):
    """Clase para gestionar y organizar las herramientas del agente."""

    def __init__(self):
        super().__init__()
        self._tools = {
            'search_tools': {
                'google_web_search': self.google_web_search
            },
            'session_tools': {
                'save_ingreso_mensual': self.save_ingreso_mensual,
                'save_precio_moto': self.save_precio_moto,
                'save_fecha_nacimiento': self.save_fecha_nacimiento,
                'save_marca_moto': self.save_marca_moto,
                'save_modelo_moto': self.save_modelo_moto,
                'check_quotation_status': self.check_quotation_status
            },
            'calculation_tools': {
                'calculate_quotation': self.calculate_quotation
            },
            'database_tools': {
                'semantic_search': self.semantic_search
            }
        }

    # --- Herramientas de Búsqueda ---
    def google_web_search(self, query: str) -> dict:
        """Realiza una búsqueda en la web usando Google Custom Search JSON API.
        
        Args:
            query (str): Término de búsqueda
            
        Returns:
            dict: Resultados de la búsqueda con título, enlace y snippet
        """
        service = build("customsearch", "v1", developerKey=current_config.GOOGLE_SEARCH_API_KEY)
        res = service.cse().list(
            q=query,
            cx=current_config.GOOGLE_CSE_ID,
            num=5
        ).execute()
        
        results = []
        for item in res.get("items", []):
            # Obtener contenido extendido de la página
            extended_content = get_page_content(item["link"])
            
            results.append({
                "title": item["title"],
                "link": item["link"],
                "snippet": item["snippet"],
                "extended_content": extended_content
            })
        
        return {"status": "success", "results": results}

    # --- Herramientas de Sesión ---
    def save_ingreso_mensual(self, tool_context: ToolContext, ingreso_mensual: float) -> dict[str, Any]:
        """Guarda el ingreso mensual en el estado de la sesión."""
        tool_context.state["ingreso_mensual"] = ingreso_mensual
        return {"estado": "Ingreso mensual guardado", "valor": ingreso_mensual}

    def save_precio_moto(self, tool_context: ToolContext, precio_moto: float) -> dict[str, Any]:
        """Guarda el precio de la moto en el estado de la sesión."""
        tool_context.state["precio_moto"] = precio_moto
        return {"estado": "Precio de moto guardado", "valor": precio_moto}

    def save_fecha_nacimiento(self, tool_context: ToolContext, fecha_nacimiento: str) -> dict[str, Any]:
        """Guarda la fecha de nacimiento en el estado de la sesión."""
        tool_context.state["fecha_nacimiento"] = fecha_nacimiento
        return {"estado": "Fecha de nacimiento guardada", "valor": fecha_nacimiento}

    def save_marca_moto(self, tool_context: ToolContext, marca_moto: str) -> dict[str, Any]:
        """Guarda la marca de la moto en el estado de la sesión."""
        tool_context.state["marca_moto"] = marca_moto
        return {"estado": "Marca de moto guardada", "valor": marca_moto}

    def save_modelo_moto(self, tool_context: ToolContext, modelo_moto: str) -> dict[str, Any]:
        """Guarda el modelo de la moto en el estado de la sesión."""
        tool_context.state["modelo_moto"] = modelo_moto
        return {"estado": "Modelo de moto guardado", "valor": modelo_moto}

    def check_quotation_status(self, tool_context: ToolContext) -> dict[str, Any]:
        """Verifica qué datos faltan para la cotización."""
        state = tool_context.state
        missing_data = []
        
        if not state.get("ingreso_mensual"):
            missing_data.append("ingreso_mensual")
        if not state.get("precio_moto"):
            missing_data.append("precio_moto")
        if not state.get("fecha_nacimiento"):
            missing_data.append("fecha_nacimiento")
        if not state.get("marca_moto"):
            missing_data.append("marca_moto")
        if not state.get("modelo_moto"):
            missing_data.append("modelo_moto")
        
        return {
            "datos_completos": len(missing_data) == 0,
            "datos_faltantes": missing_data,
            "datos_actuales": {
                "ingreso_mensual": state.get("ingreso_mensual"),
                "precio_moto": state.get("precio_moto"),
                "fecha_nacimiento": state.get("fecha_nacimiento"),
                "marca_moto": state.get("marca_moto"),
                "modelo_moto": state.get("modelo_moto")
            }
        }

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
            response.raise_for_status()
            
            try:
                return response.json()["output"]["calculos"]
            except (json.JSONDecodeError, KeyError):
                return [{"error": "Error procesando la respuesta del servidor"}]
                
        except requests.exceptions.RequestException as e:
            return [{"error": f"Error de conexión: {str(e)}"}]

    # --- Herramientas para la base de datos ---
    def semantic_search(
        self,
        query_str: str
    ):
        """
        Realiza una búsqueda semántica en la base de datos utilizando embeddings de texto.

        Esta función genera un embedding para la consulta de texto proporcionada y luego
        busca los documentos más similares en la base de datos basándose en la
        similitud coseno entre los vectores de embedding. Los resultados se filtran
        por un umbral de similitud y se devuelven los mejores k resultados.

        Args:
            query_str (str): Texto de consulta para la búsqueda semántica.

        Returns:
            list: Respuesta de la API.
        """
        data: Dict[str, Any] = {
            "body": {
                "query": query_str
            }
        }
        
        try:
            response: requests.Response = requests.post(
                url=current_config.API_MAXIKASH + "/api/semantic-search",
                json=data,
                timeout=30
            )
            response.raise_for_status()
            
            try:
                return response.json()
            except (json.JSONDecodeError, KeyError):
                return [{"error": "Error procesando la respuesta del servidor"}]
                
        except requests.exceptions.RequestException as e:
            return [{"error": f"Error de conexión: {str(e)}"}]