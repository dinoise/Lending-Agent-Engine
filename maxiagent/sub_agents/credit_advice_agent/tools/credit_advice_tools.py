import requests
import json

from typing import Any, List, Callable, Dict

from ....config import current_config

class CreditAdviceTools:
    """Clase para gestionar las herramientas del agente de asesoría de crédito."""

    def __init__(self):
        self._tools = {
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