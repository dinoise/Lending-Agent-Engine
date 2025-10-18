from ....core import settings, get_logger
from ....utils import get_page_content
from ....tools.base_tools import BaseAgentTools

from googleapiclient.discovery import build

logger = get_logger(__name__)


class CatalogTools(BaseAgentTools):
    """Clase para gestionar las herramientas del agente de consulta de catálogos."""

    def __init__(self):
        super().__init__()
        self._tools = {
            'search_tools': {
                'google_web_search': self.google_web_search
            }
        }
        logger.debug("CatalogTools inicializado")

    # --- Herramientas de Búsqueda ---
    def google_web_search(self, query: str) -> dict:
        """Realiza una búsqueda en la web usando Google Custom Search JSON API.

        Args:
            query (str): Término de búsqueda

        Returns:
            dict: Resultados de la búsqueda con título, enlace y snippet
        """
        logger.info(f"🔍 Iniciando búsqueda web - Query: '{query}'")
        try:
            logger.debug(f"Construyendo servicio de Google Custom Search - CSE ID: {settings.GOOGLE_CSE_ID}")
            service = build("customsearch", "v1", developerKey=settings.GOOGLE_SEARCH_API_KEY)

            logger.debug(f"Ejecutando búsqueda con num=3")
            res = service.cse().list(
                q=query,
                cx=settings.GOOGLE_CSE_ID,
                num=3  # Reducido a 3 para evitar MAX_TOKENS
            ).execute()

            items = res.get("items", [])
            logger.info(f"✅ Google Search retornó {len(items)} resultado(s)")

            results = []
            for idx, item in enumerate(items):
                url = item["link"]
                logger.debug(f"Procesando resultado {idx + 1}/{len(items)}: {url}")

                # Obtener contenido extendido de la página
                extended_content = get_page_content(url)
                logger.debug(f"Contenido extraído de {url}: {len(extended_content)} caracteres")

                results.append({
                    "title": item["title"],
                    "link": url,
                    "snippet": item["snippet"],
                    "extended_content": extended_content
                })

            result = {"status": "success", "results": results}
            logger.info(f"🎉 Búsqueda completada exitosamente - {len(results)} resultado(s) procesado(s)")
            logger.debug(f"Retornando resultado: {len(results)} items")
            return result

        except Exception as e:
            error_msg = f"Error en búsqueda web: {str(e)}"
            logger.error(error_msg, exc_info=True)
            result = {
                "status": "error",
                "message": error_msg,
                "results": []
            }
            logger.debug(f"Retornando error: {result}")
            return result