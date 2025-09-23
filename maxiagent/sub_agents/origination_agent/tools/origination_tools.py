import time
import base64
import uuid
from typing import List, Callable, Dict, Optional

from google.adk.tools.tool_context import ToolContext
from google.genai.types import Part, Blob

class OriginationTools:
    """Clase para gestionar las herramientas del agente de originación."""

    def __init__(self):
        self._tools = {
            'image_tools': {
                'save_image_artifact': self.save_image_artifact,
                'get_image_data': self.get_image_data
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

    async def save_image_artifact(
            self,
            tool_context: ToolContext,
            file_name: Optional[str] = None,
            mime_type: str = "image/jpeg",
            description: str = ""
    ) -> dict:
        """
        Guarda la primera imagen disponible como artifact en el sistema de ADK.

        Args:
            file_name: Nombre del archivo para guardar (opcional, si no se proporciona se genera automáticamente)
            mime_type: Tipo MIME de la imagen (opcional)
            description: Descripción opcional del artifact

        Returns:
            Dict con status y información del guardado
        """
        try:

            # Obtener contenido del usuario actual
            user_content = tool_context.user_content

            # Buscar imágenes en el contenido del usuario
            image_parts = []
            if hasattr(user_content, 'parts') and user_content.parts:
                for part in user_content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        if part.inline_data.mime_type and part.inline_data.mime_type.startswith('image/'):
                            image_parts.append(part)

            if not image_parts:
                return {
                    "status": "error",
                    "message": "No hay imágenes en el mensaje actual. Por favor adjunta una imagen."
                }

            # Tomar la primera imagen disponible
            first_image = image_parts[0]

            # Obtener datos de la imagen
            image_data = first_image.inline_data.data
            original_mime_type = first_image.inline_data.mime_type
            original_display_name = getattr(first_image.inline_data, 'display_name', 'imagen_usuario')

            # Generar nombre de archivo si no se proporciona
            if not file_name or not file_name.strip():
                # Obtener extensión del archivo original o del MIME type
                if original_display_name and '.' in original_display_name:
                    extension = original_display_name.split('.')[-1]
                else:
                    # Mapear MIME type a extensión
                    mime_to_ext = {
                        'image/jpeg': 'jpg',
                        'image/jpg': 'jpg',
                        'image/png': 'png',
                        'image/gif': 'gif',
                        'image/webp': 'webp',
                        'image/bmp': 'bmp'
                    }
                    extension = mime_to_ext.get(original_mime_type, 'jpg')

                # Generar nombre único
                unique_id = str(uuid.uuid4())[:8]
                file_name = f"image_{unique_id}.{extension}"

            # Usar el MIME type original si no se especifica uno diferente
            final_mime_type = mime_type if mime_type != "image/jpeg" else original_mime_type

            # Crear nuevo artifact con los mismos datos
            image_artifact = Part(
                inline_data=Blob(
                    mime_type=final_mime_type,
                    data=image_data
                )
            )

            # Guardar artifact con el nuevo nombre
            version = await tool_context.save_artifact(
                filename=file_name,
                artifact=image_artifact
            )

            # Actualizar estado de sesión
            if "saved_artifacts" not in tool_context.state:
                tool_context.state["saved_artifacts"] = []

            tool_context.state["saved_artifacts"].append({
                "filename": file_name,
                "version": version,
                "mime_type": final_mime_type,
                "size_bytes": len(image_data),
                "description": description,
                "original_filename": original_display_name,
                "saved_at": time.time()
            })

            return {
                "status": "success",
                "filename": file_name,
                "version": version,
                "size_bytes": len(image_data),
                "mime_type": final_mime_type,
                "original_filename": original_display_name,
                "message": f"Imagen '{original_display_name}' guardada como artifact '{file_name}' versión {version}"
            }

        except ValueError as e:
            error_msg = f"Error de configuración: {e}. ¿Está configurado ArtifactService en Runner?"
            print(error_msg)
            return {
                "status": "error",
                "message": error_msg,
                "filename": file_name
            }
        except Exception as e:
            error_msg = f"Error guardando image artifact: {e}"
            print(error_msg)
            return {
                "status": "error",
                "message": error_msg,
                "filename": file_name
            }

    async def get_image_data(
            self,
            tool_context: ToolContext,
            encoding: str = "base64"
    ) -> dict:
        """
        Obtiene los datos de la primera imagen disponible en el mensaje del usuario.

        Args:
            encoding: Formato de salida ("base64" o "bytes")

        Returns:
            Dict con los datos de la imagen y metadata
        """
        try:
            # Obtener contenido del usuario actual
            user_content = tool_context.user_content

            # Buscar imágenes en el contenido del usuario
            image_parts = []
            if hasattr(user_content, 'parts') and user_content.parts:
                for part in user_content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        if part.inline_data.mime_type and part.inline_data.mime_type.startswith('image/'):
                            image_parts.append(part)

            if not image_parts:
                return {
                    "status": "error",
                    "message": "No hay imágenes en el mensaje actual. Por favor adjunta una imagen."
                }

            # Tomar la primera imagen disponible
            first_image = image_parts[0]

            # Obtener datos de la imagen
            image_data = first_image.inline_data.data
            mime_type = first_image.inline_data.mime_type
            display_name = getattr(first_image.inline_data, 'display_name', 'imagen_usuario')

            # Preparar datos según el encoding solicitado
            if encoding.lower() == "base64":
                encoded_data = base64.b64encode(image_data).decode('utf-8')
                # Mostrar una muestra de los primeros 100 caracteres
                data_sample = encoded_data[:100] + "..." if len(encoded_data) > 100 else encoded_data
            else:
                encoded_data = image_data
                # Mostrar una muestra de los primeros 50 bytes
                data_sample = str(image_data[:50]) + "..." if len(image_data) > 50 else str(image_data)

            return {
                "status": "success",
                "filename": display_name,
                "mime_type": mime_type,
                "size_bytes": len(image_data),
                "encoding": encoding,
                "data_sample": data_sample,
                "full_data_length": len(encoded_data) if encoding == "base64" else len(image_data),
                "message": f"Imagen '{display_name}' procesada exitosamente. Tamaño: {len(image_data)} bytes"
            }

        except Exception as e:
            error_msg = f"Error obteniendo datos de imagen: {e}"
            print(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }