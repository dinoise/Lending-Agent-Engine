import requests
import json

from typing import Any, Dict

from ....core import settings
from ....tools.base_tools import BaseAgentTools


class CreditAdviceTools(BaseAgentTools):
    """Clase para gestionar las herramientas del agente de asesoría de crédito."""

    def __init__(self):
        super().__init__()
        self._tools = {
            'database_tools': {
                'semantic_search': self.semantic_search
            }
        }

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
                url=settings.API_LENDING + "/api/semantic-search",
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