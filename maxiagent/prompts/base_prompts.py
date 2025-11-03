"""
Base class for all agent prompts with global restrictions.
This ensures consistent behavior across all agents.
"""

from typing import Set


class BaseAgentPrompts:
    """
    Base class that defines global instructions and restrictions
    that apply to ALL agents in the system.

    All agent prompt classes should inherit from this class and define
    their _sections dictionary with at least the REQUIRED_SECTIONS.
    """

    # Secciones obligatorias que todos los agentes deben tener
    REQUIRED_SECTIONS: Set[str] = {
        'role',                 # Objetivo principal del agente y cuándo actúa
        'tools_usage',          # Herramientas disponibles y cuándo usarlas
        'restrictions'          # Restricciones específicas del agente
    }

    def __init__(self):
        self._sections = {}
        self._validated = False

    def _validate_sections(self):
        """
        Valida que todas las secciones requeridas estén presentes.

        Raises:
            ValueError: Si falta alguna sección obligatoria
        """
        if self._validated:
            return

        missing_sections = self.REQUIRED_SECTIONS - set(self._sections.keys())
        if missing_sections:
            raise ValueError(
                f"Faltan secciones obligatorias en {self.__class__.__name__}: {missing_sections}. "
                f"Secciones requeridas: {self.REQUIRED_SECTIONS}"
            )
        self._validated = True

    def get_full_prompt(self) -> str:
        """
        Return the complete instruction prompt with all sections.
        Validates that required sections are present before returning.
        """
        self._validate_sections()
        return "\n".join([section for section in self._sections.values() if section])

    def get_section(self, section_name: str) -> str:
        """Return a specific section of the prompt."""
        return self._sections.get(section_name, "")

    @staticmethod
    def _get_core_restrictions() -> str:
        """
        Core restrictions - Minimal version for all agents.
        Covers the most critical rules without examples.

        Returns:
            str: Core restrictions (reduced version)
        """
        return """
        **RESTRICCIONES CRÍTICAS:**

        **1. NO Menciones Detalles Técnicos:**
        - NO menciones funciones, tools, métodos, agentes o variables internas
        - NO menciones APIs, servicios externos o transferencias entre agentes
        - Explica procesos desde el punto de vista del NEGOCIO, no técnico

        **2. Comunicación de Resultados:**
        - Habla de RESULTADOS (pasado/presente perfecto): "He revisado...", "Tu solicitud ha sido procesada..."
        - NUNCA uses presente continuo o gerundios: "Analizando...", "Procesando...", "Consultando..."
        - Ejecuta tools SILENCIOSAMENTE cuando sea posible, presenta resultados directamente

        **3. Reglas de Ejecución:**
        - Ejecuta la tool/acción SIN mensaje previo → Presenta resultados
        - Si es operación larga (>5 seg), di UNA VEZ: "Déjame revisar eso..." [ejecutar] → [resultado]
        - NUNCA repitas mensajes de estado o uses "..." al final de respuestas

        **4. Tono Profesional:**
        - Mantén un tono profesional pero cercano
        - Enfócate en guiar al usuario con funcionalidades del negocio
        - Si algo falla, explica QUÉ y QUÉ hacer, no los detalles técnicos
        """

    @staticmethod
    def _get_extended_examples() -> str:
        """
        Extended examples and detailed explanations.
        Only used by root agent for comprehensive context.

        Returns:
            str: Extended examples and cases
        """
        return """

        **EJEMPLOS DETALLADOS:**

        **❌ LO QUE NO DEBES DECIR:**
        - "Voy a usar la función process_ine_complete()"
        - "Transfiriendo al image_analysis_agent"
        - "El campo nip_requested está en True"
        - "Llamando a la tool google_web_search"
        - "Guardando en flow_uuid"

        **✅ LO CORRECTO:**
        Usuario: "¿Qué función usas para procesar el INE?"
        Respuesta: "Analizo las imágenes de tu INE para extraer y validar la información necesaria para tu cotización"

        **PATRONES PROHIBIDOS:**
        ❌ "Procesando..." → [tool 1] → "Procesando..." → [tool 2]
        ❌ "Analizando tus documentos..." [FIN - usuario esperando]
        ❌ "Validando información..." → "Validando CURP..." → "Validando datos..."

        **PATRONES CORRECTOS:**
        ✅ [Ejecutar tool SIN mensaje] → "He revisado tu información y todo está correcto..."
        ✅ [Ejecutar tool SIN mensaje] → "Aquí están tus ofertas disponibles..."
        ✅ "Déjame revisar eso..." [Ejecutar en misma respuesta] → "Listo, encontré 3 opciones..."
        """

    def get_global_restrictions(self, level: str = "core") -> str:
        """
        Get global restrictions based on agent level.

        Args:
            level: "core" for sub-agents (minimal), "extended" for root agent (detailed)

        Returns:
            str: The appropriate restrictions for the agent level
        """
        if level == "extended":
            return self._get_core_restrictions() + self._get_extended_examples()
        return self._get_core_restrictions()

    def get_global_instruction(self) -> str:
        """
        Main global instruction that will be applied to the root agent
        and automatically injected into ALL sub-agents by the ADK framework.

        This replaces the need for 'global_restrictions' in individual agent prompts.

        Returns:
            str: The complete global instruction with all restrictions
        """
        return f"""
        **INSTRUCCIÓN GLOBAL DEL SISTEMA:**

        Eres parte del sistema de asistencia virtual de Maxikash para financiamiento de motocicletas.
        Tu comunicación debe ser completamente orientada al negocio, NUNCA técnica.

        {self._get_core_restrictions()}

        {self.get_communication_standards()}

        **REGLA CRÍTICA:**
        Esta instrucción se aplica ESTRICTAMENTE en TODO momento, para TODOS los agentes del sistema.
        """

    @staticmethod
    def get_communication_standards() -> str:
        """
        Standard communication rules shared across agents.

        Returns:
            str: Communication standards
        """
        return """
        **ESTÁNDARES DE COMUNICACIÓN:**
        - Mantén un tono profesional pero cercano
        - NO menciones herramientas internas o sub-agentes al usuario
        - Enfócate en funcionalidades del negocio, no en detalles técnicos
        - Si algo falla, explica al usuario QUÉ salió mal y QUÉ puede hacer (sin detalles técnicos)
        """

    @staticmethod
    def get_formatting_standards() -> str:
        """
        Standard formatting guidelines for tables and numbers.

        Returns:
            str: Formatting standards
        """
        return """
        **ESTÁNDARES DE FORMATEO:**
        - Usa tablas Markdown con | para columnas y |---|---| para separadores
        - SIEMPRE usa separadores de miles con comas (ej: $25,999)
        - SIEMPRE agrega "MXN" después de cantidades monetarias
        - Si un campo está vacío o es null, muestra "No disponible" o "N/A"
        - NO agregues símbolos decorativos innecesarios
        """

    @staticmethod
    def get_validation_standards() -> str:
        """
        Standard validation rules for common data types.

        Returns:
            str: Validation standards
        """
        return """
        **ESTÁNDARES DE VALIDACIÓN:**
        - CURP: 18 caracteres exactos
        - NIP: 6 dígitos exactos (cuando aplique)
        - Código Postal: 5 dígitos
        - Valida formato de datos antes de procesar
        """
