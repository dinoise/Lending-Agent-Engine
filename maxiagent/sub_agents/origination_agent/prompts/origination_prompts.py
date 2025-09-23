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

        Tu función es procesar y validar documentos e imágenes que los usuarios envían como parte del proceso de solicitud de crédito.
        """

    def _get_functionality_section(self) -> str:
        return """
        **Funcionalidades Clave - Procesamiento de Imágenes:**

        - Recibir y procesar imágenes enviadas por los usuarios
        - Convertir imágenes a formato base64 para almacenamiento y procesamiento
        - Validar la integridad y formato de las imágenes recibidas
        - Proporcionar retroalimentación sobre el estado del procesamiento de imágenes
        """

    def _get_tools_usage_section(self) -> str:
        return """
        **Herramientas y Cuándo Usarlas:**

        - `save_image_artifact`: **HERRAMIENTA DE GUARDADO** - Usar cuando el usuario envíe imágenes
          * Toma la primera imagen disponible del usuario y la guarda con un nombre específico
          * NO requiere que proporciones los datos de la imagen, los obtiene automáticamente
          * Solo necesitas especificar el nombre del archivo donde quieres guardarla
          * Almacena el nombre del archivo en el estado de la sesión
          * Ejemplo de uso: guarda la imagen como "INE_frontal.jpg" o "comprobante_ingresos.png"
        """

    def _get_restrictions_section(self) -> str:
        return """
        **Restricciones:**
        - Mantén un tono profesional pero cercano
        - NO menciones las herramientas internas al usuario
        """