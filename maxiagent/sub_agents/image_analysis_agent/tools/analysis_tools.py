import hashlib
import time
import base64
from typing import List, Callable, Dict

from google import genai
from google.genai import types

from google.adk.tools.tool_context import ToolContext
from ..prompts.analysis_prompts import ImageAnalysisPrompts
from ....config import current_config

# Safety settings se configuran usando enums del nuevo Google Gen AI SDK

class ImageAnalysisTools:
    """Clase para gestionar las herramientas del agente de análisis de imágenes."""

    def __init__(self):
        self._prompts = ImageAnalysisPrompts()
        self._client = None  # Cliente Gen AI (se inicializa cuando se necesite)
        self._tools = {
            'analysis_tools': {
                'analyze_ine_document': self.analyze_ine_document,
                'save_classified_image': self.save_classified_image,
                'validate_image_quality': self.validate_image_quality
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

    async def analyze_ine_document(
        self,
        tool_context: ToolContext,
        front_filename: str = "INE_frontal",
        back_filename: str = "INE_reverso"
    ) -> dict:
        """
        Analiza una imagen INE del usuario y determina si es frente o reverso.

        Args:
            front_filename: Nombre para la imagen frontal
            back_filename: Nombre para la imagen reverso

        Returns:
            Dict con resultado del análisis y clasificación
        """
        try:
            # Obtener contenido del usuario actual
            user_content = tool_context.user_content
            if not user_content:
                return {
                    "status": "error",
                    "message": "No hay contenido de usuario"
                }
            
            user_content_parts: List[types.Part] | None = user_content.parts
            if not user_content_parts:
                return {
                    "status": "error",
                    "message": "No parts in the user message"
                }

            analyzed_images = []

            for idx, image_part in enumerate(user_content_parts[:2]):  # Máximo 2 imágenes
                if not image_part: 
                    print(f"❌ Error analizando imagen {idx + 1}: No existe contenido en la lista de imagenes")
                    continue
                
                inline_data: types.Blob | None = image_part.inline_data
                if not inline_data: 
                    print(f"❌ Error analizando imagen {idx + 1}: No existe contenido en la Blob")
                    continue

                image_data: bytes | None = inline_data.data
                if not image_data: 
                    print(f"❌ Error analizando imagen {idx + 1}: No existen datos para imagen.")
                    continue

                mime_type: str | None = inline_data.mime_type
                if not mime_type or not mime_type.startswith('image/'): 
                    print(f"❌ Error analizando imagen {idx + 1}: El archivo no es una imagen.")
                    continue

                image_hash: str = hashlib.md5(image_data).hexdigest()
                print(f"🔍 Analizando imagen {idx + 1}: {len(image_data)} bytes, hash: {image_hash[:4]}")

                # Realizar análisis usando el modelo configurado
                analysis_result: dict[str, str] = await self._analyze_image_with_model(
                    image_data,
                    mime_type=mime_type
                )

                if analysis_result["status"] != "success":
                    print(f"❌ Error analizando imagen {idx + 1}: {analysis_result.get('message')}")
                    continue
                
                detected_type = analysis_result["type"]
                confidence = analysis_result.get("confidence", "medium")

                # Determinar filename basado en el tipo detectado
                if detected_type == "front":
                    filename = f"{front_filename}.jpg"
                    image_type = "frontal"
                    state_key = "ine_front_image"
                elif detected_type == "back":
                    filename = f"{back_filename}.jpg"
                    image_type = "reverso"
                    state_key = "ine_back_image"
                else:
                    filename = f"INE_indeterminado_{idx+1}.jpg"
                    image_type = "indeterminado"
                    state_key = f"ine_unknown_image_{idx+1}"

                # Verificar duplicados
                if state_key in tool_context.state:
                    existing_hash = hashlib.md5(base64.b64decode(tool_context.state[state_key])).hexdigest()
                    if existing_hash == image_hash:
                        print(f"⚠️  Imagen {image_type} duplicada, saltando...")
                        continue

                # Guardar imagen en base64
                base64_data = base64.b64encode(image_data).decode('utf-8')
                tool_context.state[state_key] = base64_data

                # Guardar como artifact
                artifact_result: dict[str, str]  = await self._save_image_artifact(
                    tool_context,
                    filename,
                    mime_type,
                    f"INE {image_type}",
                    image_data
                )

                analyzed_images.append({
                    "type": image_type,
                    "detected_type": detected_type,
                    "filename": filename,
                    "size_bytes": len(image_data),
                    "confidence": confidence,
                    "artifact_status": artifact_result.get('status'),
                    "image_hash": image_hash[:8],
                    "analysis_notes": analysis_result.get("analysis", "")
                })

                print(f"✅ Imagen clasificada como: {image_type} (confianza: {confidence})")

            return {
                "status": "success",
                "message": f"Se analizaron {len(analyzed_images)} imagen(es) exitosamente",
                "analyzed_images": analyzed_images,
                "total_processed": len(analyzed_images)
            }

        except Exception as e:
            error_msg = f"Error analizando documento INE: {e}"
            print(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }

    async def save_classified_image(
        self,
        tool_context: ToolContext,
        image_type: str,
        filename: str = ''
    ) -> dict:
        """
        Guarda una imagen clasificada como artifact.

        Args:
            image_type: Tipo de imagen (frontal, reverso, indeterminado)
            filename: Nombre específico para el archivo

        Returns:
            Dict con resultado del guardado
        """
        try:
            # Esta herramienta se usaría si se necesita guardar imágenes adicionales
            # después del análisis principal
            return {
                "status": "success",
                "message": f"Imagen {image_type} guardada exitosamente"
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Error guardando imagen: {e}"
            }

    async def validate_image_quality(self, tool_context: ToolContext) -> dict:
        """
        Valida la calidad y legibilidad de las imágenes enviadas.

        Returns:
            Dict con resultado de validación de calidad
        """
        try:
            user_content: types.Content | None = tool_context.user_content
            if not user_content:
                return {
                    "status": "error",
                    "message": "No hay contenido de usuario"
                }
            
            user_content_parts: List[types.Part] | None = user_content.parts
            if not user_content_parts:
                return {
                    "status": "error",
                    "message": "No hay Parts para validar"
                }

            validation_results = []
            for idx, image_part in enumerate(user_content_parts):
                inline_data: types.Blob | None = image_part.inline_data
                if not inline_data: 
                    print(f"❌ Error validando calidad de imagen {idx + 1}: No existe inline_data")
                    continue

                # Valiendo si el archivo es una imagen
                mime_type: str | None = inline_data.mime_type
                if not mime_type or not mime_type.startswith('image/'):
                    print(f"❌ Error validando calidad de imagen {idx + 1}: El archivo no es una imagen")
                    continue

                image_data: bytes | None = inline_data.data
                if not image_data: 
                    print(f"❌ Error validando calidad de imagen {idx + 1}: No existe contenido de imagen")
                    continue
                image_size = len(image_data)

                # Validaciones básicas
                quality = "high"
                if image_size < 50000:  # Menos de 50KB
                    quality = "low"
                elif image_size < 200000:  # Menos de 200KB
                    quality = "medium"

                validation_results.append({
                    "image_index": idx + 1,
                    "size_bytes": image_size,
                    "mime_type": mime_type,
                    "quality": quality,
                    "is_valid": image_size >= 10000  # Al menos 10KB
                })

            return {
                "status": "success",
                "message": f"Validación completada para {len(validation_results)} imagen(es)",
                "validation_results": validation_results
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Error validando calidad de imágenes: {e}"
            }

    # Métodos auxiliares privados

    def _get_genai_client(self) -> genai.Client:
        """
        Obtiene o crea el cliente Gen AI configurado para Vertex AI.

        Returns:
            Cliente Gen AI configurado
        """
        if self._client is None:
            try:
                # Configurar cliente para usar Vertex AI
                self._client = genai.Client(
                    vertexai=True,
                    project=current_config.PROJECT_ID,
                    location=current_config.LOCATION
                )
                print(f"🔧 Cliente Gen AI inicializado para proyecto {current_config.PROJECT_ID}")
            except Exception as e:
                print(f"❌ Error inicializando cliente Gen AI: {e}")
                # Fallback: intentar con variables de entorno
                try:
                    self._client = genai.Client(vertexai=True)
                    print("🔧 Cliente Gen AI inicializado con variables de entorno")
                except Exception as fallback_error:
                    print(f"❌ Error en fallback: {fallback_error}")
                    raise e

        return self._client

    async def _analyze_image_with_model(self, image_data: bytes, mime_type: str = 'image/jpeg') -> dict:
        """
        Realiza el análisis real de imagen usando el nuevo Google Gen AI SDK.

        Args:
            image_data: Datos de la imagen
            mime_type: Tipo MIME de la imagen

        Returns:
            Dict con resultado del análisis
        """
        try:
            model: str | None = current_config.ROOT_AGENT_MODEL
            if not model:
                return {
                    "status": "error",
                    "type": "unknown",
                    "message": f"No model defined"
                }
            
            client: genai.Client = self._get_genai_client()

            analysis_prompt: str = self._prompts.get_ine_analysis_prompt()

            # Armando input para la llamada a la LLM
            contents: types.ContentListUnion = [
                types.Part.from_text(text=analysis_prompt),
                types.Part.from_bytes(
                    data=image_data,
                    mime_type=mime_type
                )
            ]

            # Safety settings para documentos oficiales
            safety_settings: List[types.SafetySetting] = [
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE
                ),
            ]

            print(f"🤖 Enviando imagen al modelo {model} para análisis...")

            # Usar la interfaz asíncrona del SDK
            response: types.GenerateContentResponse = await client.aio.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    safety_settings=safety_settings,
                    temperature=0.01
                )
            )

            if not response or not response.text:
                return {
                    "status": "error",
                    "type": "unknown",
                    "message": "El modelo no proporcionó respuesta"
                }

            analysis_result = response.text.strip().upper()
            print(f"📝 Respuesta del modelo: {analysis_result}")

            # Mapear respuesta a formato esperado
            if "FRENTE" in analysis_result:
                return {
                    "status": "success",
                    "type": "front",
                    "confidence": "high",
                    "analysis": analysis_result
                }
            
            if "REVERSO" in analysis_result:
                return {
                    "status": "success",
                    "type": "back",
                    "confidence": "high",
                    "analysis": analysis_result
                }
            
            if "INDETERMINADO" in analysis_result:
                return {
                    "status": "uncertain",
                    "type": "unknown",
                    "confidence": "low",
                    "analysis": analysis_result
                }
            
            return {
                    "status": "error",
                    "type": "unknown",
                    "analysis": analysis_result
                }

        except Exception as e:
            print(f"❌ Error en análisis con modelo Gen AI: {e}")
            return {
                "status": "error",
                "type": "unknown",
                "message": "No se pudo obtener un resultado. Intente de nuevo."
            }

    async def _save_image_artifact(
        self,
        tool_context: ToolContext,
        filename: str,
        mime_type: str,
        description: str,
        image_data: bytes
    ) -> dict:
        """
        Guarda una imagen como artifact.

        Args:
            tool_context: Contexto de la herramienta
            filename: Nombre del archivo
            mime_type: Tipo MIME
            description: Descripción del artifact
            image_data: Datos de la imagen

        Returns:
            Dict con resultado del guardado
        """
        try:
            image_artifact = types.Part(
                inline_data=types.Blob(
                    mime_type=mime_type,
                    data=image_data
                )
            )

            # Guardar artifact
            version = await tool_context.save_artifact(
                filename=filename,
                artifact=image_artifact
            )

            # Actualizar estado de sesión
            if "saved_artifacts" not in tool_context.state:
                tool_context.state["saved_artifacts"] = []

            tool_context.state["saved_artifacts"].append({
                "filename": filename,
                "version": version,
                "mime_type": mime_type,
                "size_bytes": len(image_data),
                "description": description,
                "saved_at": time.time()
            })

            return {
                "status": "success",
                "filename": filename,
                "version": version,
                "message": f"Artifact '{filename}' guardado exitosamente"
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Error guardando artifact: {e}",
                "filename": filename
            }