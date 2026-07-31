import asyncio
import hashlib
import time
import base64
from typing import List

from google import genai
from google.genai import types

from google.adk.tools.tool_context import ToolContext
from ..prompts.analysis_prompts import ImageAnalysisPrompts
from ....core import settings, get_logger
from ....tools.base_tools import BaseAgentTools

logger = get_logger(__name__)

# Safety settings se configuran usando enums del nuevo Google Gen AI SDK


class ImageAnalysisTools(BaseAgentTools):
    """Clase para gestionar las herramientas del agente de análisis de imágenes."""

    def __init__(self):
        super().__init__()
        self._prompts = ImageAnalysisPrompts()
        self._tools = {
            'analysis_tools': {
                'analyze_ine_document': self.analyze_ine_document,
                'save_classified_image': self.save_classified_image,
                'validate_image_quality': self.validate_image_quality
            }
        }
        logger.debug("ImageAnalysisTools inicializado")

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

            # Logging inicial de contenido recibido
            logger.info(f"📦 Analizando contenido - Total de parts recibidos: {len(user_content_parts)}")

            # Filtrar solo imágenes válidas con sus índices originales
            image_parts = []
            for idx, part in enumerate(user_content_parts):
                if not part:
                    continue
                if not hasattr(part, 'inline_data') or not part.inline_data:
                    continue
                if not hasattr(part.inline_data, 'mime_type') or not part.inline_data.mime_type:
                    continue
                if not part.inline_data.mime_type.startswith('image/'):
                    continue
                if not hasattr(part.inline_data, 'data') or not part.inline_data.data:
                    continue
                image_parts.append((idx, part))

            image_indices = [idx for idx, _ in image_parts]
            logger.info(f"🖼️ Imágenes detectadas: {len(image_parts)} en índices {image_indices}")

            if len(image_parts) == 0:
                logger.error("⚠️ NO se encontraron imágenes en el contenido del usuario")
                result = {
                    "status": "error",
                    "message": "No se encontraron imágenes en el mensaje"
                }
                logger.debug(f"Retornando error: {result}")
                return result

            analyzed_images = []
            analysis_errors = []  # Tracking de errores

            # Procesar máximo 2 imágenes usando los índices reales
            for original_idx, image_part in image_parts[:2]:
                inline_data: types.Blob = image_part.inline_data
                image_data: bytes = inline_data.data
                mime_type: str = inline_data.mime_type

                image_hash: str = hashlib.md5(image_data).hexdigest()
                logger.info(f"🔍 Procesando imagen {original_idx + 1}/{len(image_parts)} - Hash: {image_hash[:8]}")
                logger.debug(f"Detalles imagen {original_idx}: Tamaño={len(image_data)} bytes, MIME={mime_type}")

                # Realizar análisis usando el modelo configurado
                analysis_result: dict[str, str] = await self._analyze_image_with_model(
                    image_data,
                    mime_type=mime_type
                )

                if analysis_result["status"] != "success":
                    error_info = {
                        "image_index": original_idx,
                        "image_hash": image_hash[:8],
                        "error_type": "analysis_failed",
                        "error_message": analysis_result.get('message', 'Error desconocido en análisis'),
                        "size_bytes": len(image_data),
                        "mime_type": mime_type
                    }
                    analysis_errors.append(error_info)
                    logger.error(f"❌ Error analizando imagen {original_idx}: {analysis_result.get('message')}")
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
                    filename = f"INE_indeterminado_{original_idx+1}.jpg"
                    image_type = "indeterminado"
                    state_key = f"ine_unknown_image_{original_idx+1}"

                    # Registrar como error si es indeterminado
                    error_info = {
                        "image_index": original_idx,
                        "image_hash": image_hash[:8],
                        "error_type": "type_indeterminate",
                        "error_message": f"No se pudo determinar si es frente o reverso. Análisis: {analysis_result.get('analysis', 'Sin detalles')}",
                        "size_bytes": len(image_data),
                        "mime_type": mime_type,
                        "confidence": confidence
                    }
                    analysis_errors.append(error_info)
                    logger.warning(f"⚠️ Imagen {original_idx} clasificada como indeterminada")

                # Verificar duplicados
                if state_key in tool_context.state:
                    existing_hash = hashlib.md5(base64.b64decode(tool_context.state[state_key])).hexdigest()
                    if existing_hash == image_hash:
                        logger.warning(f"⚠️ Imagen {image_type} duplicada (hash: {image_hash[:8]}), saltando...")
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
                    "analysis_notes": analysis_result.get("analysis", ""),
                    "original_index": original_idx
                })

                logger.info(f"✅ Imagen clasificada como: {image_type} (confianza: {confidence})")
                logger.debug(f"State key guardado: {state_key}, Artifact: {filename}")

            # Guardar metadata de errores en el state para que otros agentes la usen
            if analysis_errors:
                tool_context.state['ine_analysis_errors'] = analysis_errors
                logger.warning(f"⚠️ Se registraron {len(analysis_errors)} error(es) durante el análisis")

            # Determinar qué imágenes fueron procesadas exitosamente
            has_front = 'ine_front_image' in tool_context.state
            has_back = 'ine_back_image' in tool_context.state

            # Guardar metadata de procesamiento
            tool_context.state['ine_processing_metadata'] = {
                "has_front": has_front,
                "has_back": has_back,
                "total_images_received": len(image_parts),
                "total_images_analyzed": len(analyzed_images),
                "total_errors": len(analysis_errors),
                "timestamp": time.time()
            }

            # Logging final del análisis
            logger.info(f"📊 RESUMEN DE ANÁLISIS COMPLETADO")
            logger.info(f"Imágenes analizadas: {len(analyzed_images)}, Errores: {len(analysis_errors)}")
            logger.debug(f"Estado final - Frontal: {has_front}, Reverso: {has_back}")

            result = {
                "status": "success",
                "message": f"Se analizaron {len(analyzed_images)} imagen(es) exitosamente",
                "analyzed_images": analyzed_images,
                "total_processed": len(analyzed_images),
                "errors": analysis_errors if analysis_errors else None
            }
            logger.debug(f"Retornando resultado exitoso con {len(analyzed_images)} imagen(es)")
            return result

        except Exception as e:
            error_msg = f"Error analizando documento INE: {e}"
            logger.error(error_msg, exc_info=True)
            result = {
                "status": "error",
                "message": error_msg
            }
            logger.debug(f"Retornando error: {result}")
            return result

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

            # Logging inicial
            logger.info(f"🔍 Validación de calidad - Total parts: {len(user_content_parts)}")

            validation_results = []
            for idx, image_part in enumerate(user_content_parts):
                inline_data: types.Blob | None = image_part.inline_data
                if not inline_data:
                    logger.warning(f"❌ Part {idx + 1}: No tiene inline_data")
                    continue

                # Valiendo si el archivo es una imagen
                mime_type: str | None = inline_data.mime_type
                if not mime_type or not mime_type.startswith('image/'):
                    logger.warning(f"❌ Part {idx + 1}: No es una imagen (mime_type: {mime_type})")
                    continue

                image_data: bytes | None = inline_data.data
                if not image_data:
                    logger.warning(f"❌ Part {idx + 1}: No tiene datos de imagen")
                    continue
                image_size = len(image_data)

                # Validaciones básicas
                quality = "high"
                if image_size < 50000:  # Menos de 50KB
                    quality = "low"
                elif image_size < 200000:  # Menos de 200KB
                    quality = "medium"

                is_valid = image_size >= 10000  # Al menos 10KB

                validation_results.append({
                    "image_index": idx + 1,
                    "size_bytes": image_size,
                    "mime_type": mime_type,
                    "quality": quality,
                    "is_valid": is_valid
                })

                logger.debug(f"✅ Imagen {idx + 1}: {quality} quality, {'válida' if is_valid else 'inválida'}, {image_size} bytes")

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
        Crea un nuevo cliente Gen AI configurado para Vertex AI.
        Siempre crea una nueva instancia para evitar problemas con event loops cerrados.

        Returns:
            Cliente Gen AI configurado
        """
        try:
            # Siempre crear un cliente nuevo para evitar problemas con event loops cerrados
            client = genai.Client(
                vertexai=True,
                project=settings.PROJECT_ID,
                location=settings.LOCATION
            )
            logger.debug(f"🔧 Cliente Gen AI inicializado para proyecto {settings.PROJECT_ID}")
            return client
        except Exception as e:
            logger.warning(f"❌ Error inicializando cliente Gen AI: {e}")
            # Fallback: intentar con variables de entorno
            try:
                client = genai.Client(vertexai=True)
                logger.info("🔧 Cliente Gen AI inicializado con variables de entorno")
                return client
            except Exception as fallback_error:
                logger.error(f"❌ Error en fallback inicializando Gen AI client: {fallback_error}")
                raise e

    async def _analyze_image_with_model(self, image_data: bytes, mime_type: str = 'image/jpeg') -> dict:
        """
        Realiza el análisis real de imagen usando el nuevo Google Gen AI SDK.
        Incluye retry logic para manejar errores de event loop cerrado.

        Args:
            image_data: Datos de la imagen
            mime_type: Tipo MIME de la imagen

        Returns:
            Dict con resultado del análisis
        """
        max_retries = 2
        retry_delay = 0.5  # segundos

        for attempt in range(max_retries + 1):
            try:
                # Verificar y recrear event loop si está cerrado
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_closed():
                        logger.warning(f"⚠️ Event loop cerrado detectado, creando nuevo loop (intento {attempt + 1})")
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                except RuntimeError:
                    # No hay event loop en el thread actual
                    logger.warning(f"⚠️ No hay event loop, creando uno nuevo (intento {attempt + 1})")
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                # Usar modelo optimizado para análisis de imágenes (más económico)
                model: str = settings.IMAGE_ANALYSIS_MODEL or settings.ROOT_AGENT_MODEL
                if not model:
                    return {
                        "status": "error",
                        "type": "unknown",
                        "message": f"No model defined"
                    }

                logger.debug(f"🎯 Usando modelo: {model}")

                # Crear un nuevo cliente en cada intento para evitar problemas
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

                logger.debug(f"🤖 Enviando imagen al modelo {model} para análisis (intento {attempt + 1})")

                # Usar la interfaz asíncrona del SDK con optimizaciones de costo
                response: types.GenerateContentResponse = await client.aio.models.generate_content(
                    model=model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        safety_settings=safety_settings,
                        temperature=0.01,
                        max_output_tokens=50,  # solo necesitamos "FRENTE", "REVERSO" o "INDETERMINADO"
                        media_resolution=types.MediaResolution.MEDIA_RESOLUTION_MEDIUM  # reduce tokens de imagen
                    )
                )

                # Extraer correctamente el texto de la respuesta procesando todos los parts
                if not response or not response.candidates:
                    return {
                        "status": "error",
                        "type": "unknown",
                        "message": "El modelo no proporcionó respuesta"
                    }

                # Acceder a los parts de la primera candidate
                candidate = response.candidates[0]
                if not candidate.content or not candidate.content.parts:
                    return {
                        "status": "error",
                        "type": "unknown",
                        "message": "El modelo no proporcionó contenido"
                    }

                # Extraer solo los text parts, ignorando thought_signature y function_call
                text_parts = []
                for part in candidate.content.parts:
                    if hasattr(part, 'text') and part.text:
                        text_parts.append(part.text)

                if not text_parts:
                    return {
                        "status": "error",
                        "type": "unknown",
                        "message": "El modelo no proporcionó texto en la respuesta"
                    }

                # Concatenar todos los text parts
                analysis_result = " ".join(text_parts).strip().upper()
                logger.debug(f"📝 Respuesta del modelo: {analysis_result}")

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

            except RuntimeError as e:
                # Manejo específico para errores de event loop
                error_msg = str(e)
                if "Event loop is closed" in error_msg or "no running event loop" in error_msg:
                    logger.warning(f"⚠️ Error de event loop detectado: {error_msg}")
                    if attempt < max_retries:
                        logger.info(f"🔄 Reintentando en {retry_delay}s... (intento {attempt + 2}/{max_retries + 1})")
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        logger.error(f"❌ Máximo de reintentos alcanzado para error de event loop")
                        return {
                            "status": "error",
                            "type": "unknown",
                            "message": f"Error de event loop después de {max_retries + 1} intentos: {error_msg}"
                        }
                else:
                    # Otro tipo de RuntimeError
                    logger.error(f"❌ RuntimeError en análisis: {e}", exc_info=True)
                    return {
                        "status": "error",
                        "type": "unknown",
                        "message": f"Error en análisis: {error_msg}"
                    }

            except Exception as e:
                error_msg = str(e)
                logger.error(f"❌ Error en análisis con modelo Gen AI: {error_msg}", exc_info=True)

                # Reintentar para ciertos errores de red/timeout
                if attempt < max_retries and any(keyword in error_msg.lower() for keyword in ["timeout", "connection", "network"]):
                    logger.info(f"🔄 Reintentando debido a error de red... (intento {attempt + 2}/{max_retries + 1})")
                    await asyncio.sleep(retry_delay)
                    continue

                return {
                    "status": "error",
                    "type": "unknown",
                    "message": f"No se pudo obtener un resultado: {error_msg}"
                }

        # Si llegamos aquí, se agotaron todos los reintentos
        return {
            "status": "error",
            "type": "unknown",
            "message": "Se agotaron todos los reintentos para analizar la imagen"
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