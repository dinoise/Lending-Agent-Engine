"""
Base class for all agent tools.
This ensures consistent tool management across all agents.
"""

from typing import List, Callable, Dict


class BaseAgentTools:
    """
    Base class that provides common tool management functionality
    for all agent tool classes.

    All agent tool classes should inherit from this class and define
    their _tools dictionary in __init__.
    """

    def __init__(self):
        """
        Initialize the tools dictionary.
        Child classes should call super().__init__() and then define their _tools.
        """
        self._tools: Dict[str, Dict[str, Callable]] = {}

    def get_all_tools(self) -> List[Callable]:
        """
        Retorna una lista con todas las funciones herramienta.

        Returns:
            List[Callable]: Lista de todas las funciones tool disponibles
        """
        all_tools = []
        for category in self._tools.values():
            all_tools.extend(category.values())
        return all_tools

    def get_tools_by_category(self, category: str) -> Dict[str, Callable]:
        """
        Retorna las herramientas de una categoría específica.

        Args:
            category (str): Nombre de la categoría de tools

        Returns:
            Dict[str, Callable]: Diccionario de tools en esa categoría
        """
        return self._tools.get(category, {})

    def get_tool(self, tool_name: str) -> Callable:
        """
        Retorna una herramienta específica por nombre.

        Args:
            tool_name (str): Nombre de la tool a buscar

        Returns:
            Callable: La función tool solicitada

        Raises:
            ValueError: Si la tool no se encuentra
        """
        for category in self._tools.values():
            if tool_name in category:
                return category[tool_name]
        raise ValueError(f"Herramienta '{tool_name}' no encontrada")

    def get_tool_descriptions(self) -> List[Dict]:
        """
        Retorna descripciones de todas las herramientas para el agente.

        Returns:
            List[Dict]: Lista de diccionarios con name, description, y function
        """
        descriptions = []
        for _, tools in self._tools.items():
            for tool_name, tool_func in tools.items():
                descriptions.append({
                    'name': tool_name,
                    'description': tool_func.__doc__ or f"Función {tool_name}",
                    'function': tool_func
                })
        return descriptions
