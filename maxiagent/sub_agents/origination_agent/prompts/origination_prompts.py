class OriginationPrompts:
    """Class to manage Origination Agent instruction prompts."""

    def __init__(self):
        self._sections = {
            'role': self._get_role_section(),
            'functionality': self._get_functionality_section(),
            'tools_usage': self._get_tools_usage_section(),
            'restrictions': self._get_restrictions_section()
        }

    def get_full_prompt(self) -> str:
        """Return the complete instruction prompt."""
        return "\n".join([
            self._sections['role'],
            self._sections['functionality'],
            self._sections['tools_usage'],
            self._sections['restrictions']
        ])

    def get_section(self, section_name: str) -> str:
        """Return a specific section of the prompt."""
        return self._sections.get(section_name, "")

    def _get_role_section(self) -> str:
        return """
        **Objetivo Principal:**
        Eres el especialista en originación para el sistema de Maxikash.

        Tu función será definida próximamente según los requerimientos específicos del proceso de originación.
        """

    def _get_functionality_section(self) -> str:
        return """
        **Funcionalidades Clave:**

        Las funcionalidades específicas de este agente serán implementadas próximamente.
        """

    def _get_tools_usage_section(self) -> str:
        return """
        **Herramientas y Cuándo Usarlas:**

        Las herramientas específicas para este agente serán definidas próximamente.
        """

    def _get_restrictions_section(self) -> str:
        return """
        **Restricciones:**
        - Mantén un tono profesional pero cercano
        - NO menciones las herramientas internas al usuario
        - Las restricciones específicas serán definidas según los requerimientos
        """