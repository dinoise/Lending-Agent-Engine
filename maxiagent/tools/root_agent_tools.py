import requests
import json

from datetime import datetime
from typing import Any, List, Callable, Dict

from ..config import current_config
from ..utils import get_page_content
from ..db import (get_db_session,
                  EmbeddingData,
                  EmbeddingDataSchema)

from googleapiclient.discovery import build
from google.adk.tools.tool_context import ToolContext

from langchain_google_vertexai import VertexAIEmbeddings
from sqlalchemy import func

class RootAgentTools:
    """Clase para gestionar y organizar las herramientas del agente."""
    
    def __init__(self):
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
    
    def get_tool_descriptions(self) -> List[Dict]:
        """Retorna descripciones de todas las herramientas para el agente."""
        descriptions = []
        for _, tools in self._tools.items():
            for tool_name, tool_func in tools.items():
                descriptions.append({
                    'name': tool_name,
                    'description': tool_func.__doc__ or f"Función {tool_name}",
                    'function': tool_func
                })
        return descriptions

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
        query_str: str,
        similarity_threshold: float = 0.5,
        top_k: int = 1
    ):
        """
        Realiza una búsqueda semántica en la base de datos utilizando embeddings de texto.

        Esta función genera un embedding para la consulta de texto proporcionada y luego
        busca los documentos más similares en la base de datos basándose en la
        similitud coseno entre los vectores de embedding. Los resultados se filtran
        por un umbral de similitud y se devuelven los mejores k resultados.

        Args:
            query_str (str): Texto de consulta para la búsqueda semántica.
            similarity_threshold (float, optional): Umbral de similitud para filtrar 
                resultados (0-1). Valores más bajos indican mayor similitud. 
                Por defecto es 0.5.
            top_k (int, optional): Número máximo de resultados a devolver. 
                Por defecto es 5.

        Returns:
            list: Lista de objetos EmbeddingDataSchema serializados que representan
                los documentos más similares encontrados en la base de datos.
        """
        db = get_db_session()
        if not db:
            raise Exception("Inicializa la base de datos primero.")
        
        try:
            # Generar el embedding de la consulta
            embedding_service = VertexAIEmbeddings(
                model_name=current_config.EMBEDDING_MODEL_NAME
            )
            query_embedding: List[float] = embedding_service.embed_query(query_str)
            
            # Usar la función de distancia correcta
            distance = EmbeddingData.embedding_embedded_text.cosine_distance(query_embedding)
            
            results = db.query(
                EmbeddingData.embedding_data_text,
                distance.label('similarity')
            ).filter(
                distance < similarity_threshold
            ).order_by(
                distance.asc()  # Menor distancia = mayor similitud
            ).limit(
                top_k
            ).all()
                        
            return EmbeddingDataSchema(many=True).dump(results)
        except Exception as e:
            print(f"Error al realizar la búsqueda semántica: {e}")
            raise
        finally:
            db.close()