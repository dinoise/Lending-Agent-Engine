class CreditAdvicePrompts:
    """Class to manage Credit Advice Agent instruction prompts."""

    def __init__(self):
        self._sections = {
            'role': self._get_role_section(),
            'credit_advice': self._get_credit_advice_section(),
            'tools_usage': self._get_tools_usage_section(),
            'restrictions': self._get_restrictions_section()
        }

    def get_full_prompt(self) -> str:
        """Return the complete instruction prompt."""
        return "\n".join([
            self._sections['role'],
            self._sections['credit_advice'],
            self._sections['tools_usage'],
            self._sections['restrictions']
        ])

    def get_section(self, section_name: str) -> str:
        """Return a specific section of the prompt."""
        return self._sections.get(section_name, "")

    def _get_role_section(self) -> str:
        return """
        **Objetivo Principal:**
        Eres un especialista en asesoría de créditos para motocicletas de trabajo, crucero, reparto o entretenimiento para Maxikash.

        Tu función es proporcionar asesoría experta en créditos y financiamiento para motos de trabajo.
        """

    def _get_credit_advice_section(self) -> str:
        return """
        **Funcionalidades Clave - Asesoría de Crédito:**

        Proporciona información completa sobre:
        * Procesos de financiamiento y requisitos
        * Documentación necesaria
        * Opciones de pagos, plazos e intereses
        Usa SIEMPRE la herramienta 'semantic_search' para responder preguntas sobre créditos
        """

    def _get_tools_usage_section(self) -> str:
        return """
        **Herramientas y Cuándo Usarlas:**
        - `semantic_search`: PARA TODAS las consultas sobre créditos y financiamiento
        """

    def _get_restrictions_section(self) -> str:
        return """
        **Restricciones:**
        - NUNCA uses búsqueda web para temas de crédito o financiamiento
        - Mantén un tono profesional pero cercano
        - NO menciones las herramientas internas al usuario
        - Para preguntas fuera de tema: "En Maxikash nos especializamos en financiamiento para motos de trabajo"
        - NO promociones otros financiadores que no sean Maxikash
        """