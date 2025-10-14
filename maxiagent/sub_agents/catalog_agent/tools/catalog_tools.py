from ....core import settings
from ....utils import get_page_content
from ....tools.base_tools import BaseAgentTools

from googleapiclient.discovery import build


class CatalogTools(BaseAgentTools):
    """Clase para gestionar las herramientas del agente de consulta de catálogos."""

    def __init__(self):
        super().__init__()
        self._tools = {
            'search_tools': {
                'google_web_search': self.google_web_search
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
        try:
            service = build("customsearch", "v1", developerKey=settings.GOOGLE_SEARCH_API_KEY)
            res = service.cse().list(
                q=query,
                cx=settings.GOOGLE_CSE_ID,
                num=3  # Reducido a 2 para evitar MAX_TOKENS
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

        except Exception as e:
            return {
                "status": "error",
                "message": f"Error en búsqueda web: {str(e)}",
                "results": []
            }