# Estándar de Categorías para Tools

Este documento define las categorías estándar para organizar las herramientas (tools) de cada agente.

## Categorías Disponibles

Cada clase de tools debe organizar sus herramientas en categorías semánticas según su función:

### `search_tools`
Herramientas para realizar búsquedas en web o documentos.
- Ejemplo: `google_web_search`

### `database_tools`
Herramientas para consultas a bases de datos o APIs de datos.
- Ejemplo: `semantic_search`

### `session_tools`
Herramientas para manejo de estado y sesión del usuario.
- Ejemplo: `save_ingreso_mensual`, `save_precio_moto`, `check_quotation_status`

### `calculation_tools`
Herramientas para cálculos y procesamiento numérico.
- Ejemplo: `calculate_quotation`

### `analysis_tools`
Herramientas para análisis de imágenes, documentos o datos.
- Ejemplo: `analyze_ine_document`, `validate_image_quality`

### `quotation_flow`
Herramientas específicas del flujo de cotización.
- Ejemplo: `initialize_flow`, `resend_nip`, `select_offer`

### `chained_tools`
Herramientas que ejecutan múltiples pasos automáticamente.
- Ejemplo: `process_ine_complete`, `complete_form_and_nip`

### `validation_tools`
Herramientas para validación de datos.
- Ejemplo: `validate_curp`, `validate_blacklist`

### `processing_tools`
Herramientas para procesamiento general de datos.
- Ejemplo: Procesamiento de formularios, transformaciones de datos

## Estructura Estándar

Todas las clases de tools deben seguir esta estructura:

```python
from ....tools.base_tools import BaseAgentTools

class MyAgentTools(BaseAgentTools):
    """Clase para gestionar las herramientas del agente."""

    def __init__(self):
        super().__init__()
        self._tools = {
            'category_name': {
                'tool_name': self.tool_method,
                'another_tool': self.another_method
            },
            'another_category': {
                'third_tool': self.third_method
            }
        }

    def tool_method(self, ...):
        """Docstring describing the tool."""
        pass
```

## Estado Actual por Agente

### RootAgentTools
- `search_tools`: google_web_search
- `session_tools`: save_*, check_quotation_status
- `calculation_tools`: calculate_quotation
- `database_tools`: semantic_search

### CatalogTools
- `search_tools`: google_web_search

### CreditAdviceTools
- `database_tools`: semantic_search

### OriginationTools
- `chained_tools`: process_ine_complete, complete_form_and_nip, confirm_nip_and_get_offers
- `quotation_flow`: initialize_flow, resend_nip, select_offer

### ImageAnalysisTools
- `analysis_tools`: analyze_ine_document, save_classified_image, validate_image_quality

## Ventajas del Sistema de Categorías

1. **Organización semántica**: Fácil entender qué hace cada tool
2. **Escalabilidad**: Agregar nuevas tools en la categoría apropiada
3. **Búsqueda eficiente**: `get_tools_by_category()` permite filtrar por tipo
4. **Flexibilidad**: Cada agente usa solo las categorías que necesita
5. **Mantenibilidad**: Código más limpio y organizado
