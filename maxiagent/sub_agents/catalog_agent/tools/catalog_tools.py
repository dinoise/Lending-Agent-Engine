from typing import Any, List, Callable, Dict

from ....config import current_config
from ....utils import get_page_content

from googleapiclient.discovery import build

class CatalogTools:
    """Clase para gestionar las herramientas del agente de consulta de catálogos."""

    def __init__(self):
        self._tools = {
            'search_tools': {
                'google_web_search': self.google_web_search
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