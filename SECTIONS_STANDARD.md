# Estándar de Secciones para Prompts de Agentes

Este documento define el estándar de organización de prompts en el sistema de agentes Maxikash.

## Secciones Obligatorias

Las secciones obligatorias están definidas en `BaseAgentPrompts.REQUIRED_SECTIONS` y son validadas automáticamente al llamar `get_full_prompt()`:

### `role`
Define el objetivo principal del agente y cuándo debe actuar.
- **Contenido:**
  - Objetivo principal del agente
  - Función específica dentro del sistema
  - Cuándo debe activarse o intervenir
- **Ejemplo:**
  ```
  **Objetivo Principal:**
  Eres el especialista en consulta de catálogos de motocicletas para Maxikash.

  Tu función es proporcionar información actualizada sobre modelos, precios y
  características técnicas de Vento, Italika y Bajaj.
  ```

### `tools_usage`
Describe las herramientas disponibles para el agente y cuándo usarlas.
- **Contenido:**
  - Lista de herramientas disponibles
  - Cuándo usar cada herramienta
  - Prioridad o orden de uso si aplica
- **Ejemplo:**
  ```
  **Herramientas Disponibles:**
  - SIEMPRE usa búsqueda para consultas de catálogo
  - Para precios actualizados, consulta las páginas oficiales
  ```

### `restrictions`
Restricciones y buenas prácticas específicas del agente.
- **Contenido:**
  - Restricciones de comportamiento específicas del dominio
  - Qué debe y qué NO debe hacer el agente
  - Tono y estilo de comunicación
  - Manejo de casos edge o errores específicos
- **Ejemplo:**
  ```
  **Restricciones:**
  - Mantén un tono profesional pero cercano
  - NO menciones las herramientas internas al usuario
  - Solo trabajamos con Italika, Bajaj y Vento
  ```

### `global_restrictions`
Restricciones globales del sistema (heredadas de `BaseAgentPrompts.get_global_restrictions()`).
- **Contenido:**
  - Prohibición de mencionar detalles técnicos
  - Reglas de comunicación aplicables a todos los agentes
  - Ejemplos de lo que SÍ y lo que NO se debe decir
- **Nota:** Esta sección se obtiene automáticamente llamando a `self.get_global_restrictions()`

## Secciones Opcionales

Los agentes pueden definir secciones adicionales según sus necesidades específicas:

### Ejemplos de Secciones Opcionales Actuales:

- **`coordination`** (RootAgentPrompts): Instrucciones de coordinación entre agentes
- **`functionality`** (OriginationPrompts, ImageAnalysisPrompts): Flujo de trabajo detallado
- **`credit_advice`** (CreditAdvicePrompts): Funcionalidades de asesoría crediticia
- **`catalog_consultation`** (CatalogPrompts): Funcionalidades de consulta de catálogo
- **`offer_formatting`** (OriginationPrompts): Formato específico para presentar ofertas

## Validación Automática

`BaseAgentPrompts` valida automáticamente que todas las secciones obligatorias estén presentes. Si falta alguna sección, se levantará un `ValueError` al llamar `get_full_prompt()`:

```
Faltan secciones obligatorias en {ClassName}: {missing_sections}.
Secciones requeridas: {REQUIRED_SECTIONS}
```

## Cómo Implementar en una Nueva Clase de Prompts

```python
class MiAgentPrompts(BaseAgentPrompts):
    def __init__(self):
        super().__init__()
        self._sections = {
            # OBLIGATORIAS
            'role': self._get_role_section(),
            'tools_usage': self._get_tools_usage_section(),
            'restrictions': self._get_restrictions_section(),
            'global_restrictions': self.get_global_restrictions(),

            # OPCIONALES (según necesidad)
            'mi_seccion_especial': self._get_mi_seccion_especial(),
        }

    def _get_role_section(self) -> str:
        return """[Contenido del rol]"""

    def _get_tools_usage_section(self) -> str:
        return """[Contenido de herramientas]"""

    def _get_restrictions_section(self) -> str:
        return """[Contenido de restricciones]"""

    def _get_mi_seccion_especial(self) -> str:
        return """[Contenido opcional específico]"""
```

## Cómo Agregar una Nueva Sección Obligatoria

Si necesitas hacer una nueva sección obligatoria para todos los agentes:

1. Edita `maxiagent/prompts/base_prompts.py`
2. Agrega la nueva sección a `BaseAgentPrompts.REQUIRED_SECTIONS`
3. Actualiza TODOS los agentes existentes para incluir esa sección
4. Actualiza este documento con la descripción de la nueva sección

## Estructura Actual

- **RootAgentPrompts**: role, coordination, tools_usage, restrictions, global_restrictions
- **CatalogPrompts**: role, catalog_consultation, tools_usage, restrictions, global_restrictions
- **CreditAdvicePrompts**: role, credit_advice, tools_usage, restrictions, global_restrictions
- **OriginationPrompts**: role, functionality, tools_usage, offer_formatting, restrictions, global_restrictions
- **ImageAnalysisPrompts**: role, functionality, tools_usage, restrictions, global_restrictions

## Beneficios de Esta Estructura

1. **Consistencia**: Todos los agentes tienen las mismas secciones base
2. **Validación**: Errores detectados automáticamente en tiempo de ejecución
3. **Flexibilidad**: Permite secciones opcionales para necesidades específicas
4. **Mantenibilidad**: Fácil de entender qué secciones tiene cada agente
5. **Documentación**: Estructura autodocumentada y estandarizada
