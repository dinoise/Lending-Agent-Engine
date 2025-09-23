from typing import Any, List, Callable, Dict

from google.adk.tools.tool_context import ToolContext

class SessionManagementTools:
    """Clase para gestionar las herramientas del agente de manejo de sesión."""

    def __init__(self):
        self._tools = {
            'session_tools': {
                'save_ingreso_mensual': self.save_ingreso_mensual,
                'save_precio_moto': self.save_precio_moto,
                'save_fecha_nacimiento': self.save_fecha_nacimiento,
                'save_marca_moto': self.save_marca_moto,
                'save_modelo_moto': self.save_modelo_moto,
                'check_quotation_status': self.check_quotation_status
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