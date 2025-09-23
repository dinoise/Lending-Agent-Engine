import hashlib
import time
import re
import base64
import uuid
import asyncio
import requests

from typing import List, Callable, Dict, Optional
from datetime import datetime

from google.adk.tools.tool_context import ToolContext
from google.genai.types import Part, Blob
from ....config import current_config

class OriginationTools:
    """Clase para gestionar las herramientas del agente de originación."""

    def __init__(self):
        self._tools = {
            'image_tools': {
                'save_image_artifact': self.save_image_artifact,
                'get_image_data': self.get_image_data,
                'capture_ine_images': self.capture_ine_images
            },
            'quotation_flow': {
                'initialize_flow': self.initialize_flow,
                'process_ine_documents': self.process_ine_documents,
                'verify_ine_processing': self.verify_ine_processing,
                'validate_curp': self.validate_curp,
                'submit_form_data': self.submit_form_data,
                'query_offers': self.query_offers
            },
            'validation_tools': {
                'validate_required_data': self.validate_required_data,
                'validate_curp_format': self.validate_curp_format,
                'validate_rfc_format': self.validate_rfc_format
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

    # === New Quotation Flow Methods ===

    async def capture_ine_images(self, tool_context: ToolContext, front_filename: str = "INE_frontal", back_filename: str = "INE_reverso") -> dict:
        """
        Método auxiliar para capturar y procesar ambas imágenes del INE.

        Args:
            front_filename: Nombre para guardar la imagen frontal
            back_filename: Nombre para guardar la imagen del reverso

        Returns:
            Dict con resultado del procesamiento
        """
        try:
            # Obtener contenido del usuario actual
            user_content = tool_context.user_content

            print(f"user_content type: {type(user_content)}")
            print(f"user_content parts count: {len(user_content.parts) if hasattr(user_content, 'parts') else 'no parts'}")

            # Buscar imágenes en el contenido del usuario
            image_parts = []
            if hasattr(user_content, 'parts') and user_content.parts:
                for i, part in enumerate(user_content.parts):
                    print(f"Part {i}: {type(part)}")
                    if hasattr(part, 'inline_data') and part.inline_data:
                        print(f"  MIME type: {part.inline_data.mime_type}")
                        print(f"  Data size: {len(part.inline_data.data) if part.inline_data.data else 0} bytes")
                        if part.inline_data.mime_type and part.inline_data.mime_type.startswith('image/'):
                            image_parts.append(part)
                            print(f"  → Imagen {len(image_parts)} agregada")

            print(f"Total imágenes encontradas: {len(image_parts)}")

            if len(image_parts) < 1:
                return {
                    "status": "error",
                    "message": "Se requiere al menos una imagen. Envía las imágenes del INE (frente y reverso)."
                }

            # Procesar imágenes
            processed_images = []

            for idx, image_part in enumerate(image_parts[:2]):  # Máximo 2 imágenes
                # VERIFICAR que sea una imagen nueva (no duplicada)
                image_data = image_part.inline_data.data
                image_hash = hashlib.md5(image_data).hexdigest()  # Para detectar duplicados
                
                print(f"Procesando imagen {idx + 1}: {len(image_data)} bytes, hash: {image_hash[:8]}")

                base64_data = base64.b64encode(image_data).decode('utf-8')

                # Determinar si es frente o reverso basado en el orden
                if idx == 0:
                    # VERIFICAR que no sea la misma imagen que ya tenemos
                    if 'ine_front_image' in tool_context.state:
                        existing_hash = hashlib.md5(base64.b64decode(tool_context.state['ine_front_image'])).hexdigest()
                        if existing_hash == image_hash:
                            print("⚠️  Imagen frontal duplicada, saltando...")
                            continue
                    
                    tool_context.state['ine_front_image'] = base64_data
                    filename = f"{front_filename}.jpg"
                    image_type = "frontal"
                else:
                    # VERIFICAR que no sea la misma imagen que el frontal
                    if 'ine_front_image' in tool_context.state:
                        front_hash = hashlib.md5(base64.b64decode(tool_context.state['ine_front_image'])).hexdigest()
                        if front_hash == image_hash:
                            print("⚠️  Imagen reverso es igual al frontal, saltando...")
                            # Si es la misma imagen, tratar como error o continuar
                            continue
                    
                    tool_context.state['ine_back_image'] = base64_data
                    filename = f"{back_filename}.jpg"
                    image_type = "reverso"

                # Guardar como artifact
                artifact_result = await self.save_image_artifact(
                    tool_context,
                    filename,
                    image_part.inline_data.mime_type,
                    f"INE {image_type}"
                )

                processed_images.append({
                    "type": image_type,
                    "filename": filename,
                    "size_bytes": len(image_data),
                    "artifact_status": artifact_result.get('status'),
                    "image_hash": image_hash[:8]  # Para debugging
                })

            print(f"Imágenes procesadas: {len(processed_images)}")

            # Verificar que tengamos al menos una imagen
            if len(processed_images) == 0:
                return {
                    "status": "error",
                    "message": "No se pudieron procesar las imágenes (posiblemente duplicados)."
                }
            elif len(processed_images) == 1:
                return {
                    "status": "partial",
                    "message": f"Solo se procesó una imagen ({processed_images[0]['type']}). Se requiere también la imagen del {'reverso' if processed_images[0]['type'] == 'frontal' else 'frontal'}.",
                    "processed_images": processed_images
                }

            return {
                "status": "success",
                "message": f"Se procesaron {len(processed_images)} imágenes del INE exitosamente",
                "processed_images": processed_images,
                "has_both_sides": len(processed_images) >= 2
            }

        except Exception as e:
            error_msg = f"Error capturando imágenes INE: {e}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "message": error_msg
            }

    async def initialize_flow(self, tool_context: ToolContext) -> dict:
        """
        Inicializa el flujo de cotización obteniendo un UUID único.

        Returns:
            Dict con el UUID del flujo o error
        """
        try:
            api_url = f"{current_config.URL_ORIGINADOR}/originacion/nuevo-flujo"

            headers = {
                'User-Agent': 'Python-HTTP-Post-Client/1.0',
                'X-API-KEY': current_config.KEY_ORIGINADOR,
            }

            response = requests.get(api_url, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json()
            flow_uuid = data.get('uuidFlujo')

            if not flow_uuid:
                raise ValueError("No se recibió flow_uuid del servidor")

            # Guardar en estado de sesión
            tool_context.state['flow_uuid'] = flow_uuid

            return {
                "status": "success",
                "flow_uuid": flow_uuid,
                "message": f"Flujo inicializado exitosamente con UUID: {flow_uuid}"
            }

        except Exception as e:
            error_msg = f"Error inicializando flujo: {e}"
            print(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }

    async def process_ine_documents(self, tool_context: ToolContext) -> dict:
        """
        Procesa las imágenes INE (frente y reverso) enviándolas al API.

        Returns:
            Dict con el resultado del procesamiento
        """
        try:
            flow_uuid = tool_context.state.get('flow_uuid')
            if not flow_uuid:
                return {
                    "status": "error",
                    "message": "Flujo no inicializado. Ejecuta initialize_flow primero."
                }

            
            # Obtener imágenes de artifacts o del estado
            ine_front = tool_context.state.get('ine_front_image')
            ine_back = tool_context.state.get('ine_back_image')

            if not ine_front or not ine_back:
                return {
                    "status": "error",
                    "message": "Se requieren ambas imágenes del INE (frente y reverso)"
                }

            api_url = f"{current_config.URL_ORIGINADOR}/originacion/subir-ine"
            params = {"uuidFlujo": flow_uuid}
            
            headers = {
                'User-Agent': 'Python-HTTP-Post-Client/1.0',
                'X-API-KEY': current_config.KEY_ORIGINADOR,
            }

            payload = {
                "frenteBase64": ine_front,
                "reversoBase64": ine_back
            }

            response = requests.post(
                api_url,
                params=params,
                json=payload,
                headers=headers,
                timeout=60
            )
            response.raise_for_status()

            data = response.json()

            print(f"response ine documents {data}")

            return {
                "status": "success",
                "message": "Documentos INE enviados para procesamiento"
            }

        except Exception as e:
            error_msg = f"Error procesando documentos INE: {e}"
            print(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }

    async def verify_ine_processing(self, tool_context: ToolContext, max_retries: int = 10) -> dict:
        """
        Verifica el estado del procesamiento INE con reintentos.

        Args:
            max_retries: Número máximo de reintentos

        Returns:
            Dict con los datos procesados o error
        """
        try:
            flow_uuid = tool_context.state.get('flow_uuid')
            if not flow_uuid:
                return {
                    "status": "error",
                    "message": "Flujo no inicializado"
                }

            api_url = f"{current_config.URL_ORIGINADOR}/originacion/estatus-ine"
            params = {"uuidFlujo": flow_uuid}

            headers = {
                'User-Agent': 'Python-HTTP-Post-Client/1.0',
                'X-API-KEY': current_config.KEY_ORIGINADOR,
            }
            
            for attempt in range(max_retries):
                try:
                    response = requests.get(api_url, params=params, headers=headers, timeout=30)
                    response.raise_for_status()

                    data = response.json()

                    print(f"response ine processing {data}. attempt {attempt}")

                    if data.get('completado', False):
                        form_data = data.get('formularioCaptura', {})
                        tool_context.state['user_data'] = form_data

                        return {
                            "status": "success",
                            "completed": True,
                            "user_data": form_data,
                            "message": "Procesamiento completado exitosamente"
                        }

                    # Esperar antes del siguiente intento
                    wait_time = min(2 ** attempt, 30)  # Exponential backoff, max 30s
                    await asyncio.sleep(wait_time)

                except requests.RequestException as e:
                    if attempt == max_retries - 1:
                        raise e
                    await asyncio.sleep(2 ** attempt)

            return {
                "status": "timeout",
                "message": f"El procesamiento no se completó después de {max_retries} intentos"
            }

        except Exception as e:
            error_msg = f"Error verificando procesamiento INE: {e}"
            print(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }

    async def validate_curp(self, tool_context: ToolContext, curp: str) -> dict:
        """
        Valida CURP contra lista negra y ofertas activas.

        Args:
            curp: CURP a validar

        Returns:
            Dict con resultado de validaciones
        """
        try:
            api_base = current_config.URL_ORIGINADOR

            flow_uuid = tool_context.state.get('flow_uuid')
            if not flow_uuid:
                return {
                    "status": "error",
                    "message": "Flujo no inicializado"
                }
            
            # Preparar llamadas paralelas
            blacklist_url: str = f"{api_base}/originacion/validarCurpListaNegra"
            offers_url: str = f"{api_base}/originacion/validarOfertasActivas"
            renapo_url: str = f"{api_base}/originacion/validacion-curp"

            params: Dict[str, str] = {"curp": curp, "uuidFlujo": flow_uuid}

            # Ejecutar ambas validaciones en paralelo usando asyncio
            async def call_api(url: str, params: dict):
                headers = {
                    'User-Agent': 'Python-HTTP-Post-Client/1.0',
                    'X-API-KEY': current_config.KEY_ORIGINADOR,
                }
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(
                    None,
                    lambda: requests.post(url, params=params, headers=headers, timeout=30)
                )

            blacklist_response, offers_response, renapo_response = await asyncio.gather(
                call_api(blacklist_url, params),
                call_api(offers_url, params),
                call_api(renapo_url, params),
                return_exceptions=True
            )

            # Procesar respuestas
            results = {
                "status": "success",
                "curp": curp,
                "blacklist_check": "error",
                "active_offers_check": "error"
            }

            # Procesar resultado de lista negra
            if isinstance(blacklist_response, requests.Response):
                blacklist_response.raise_for_status()
                blacklist_data = blacklist_response.json()
                results["blacklist_check"] = blacklist_data.get('mensaje') if blacklist_data.get('mensaje') else "Es lista negra"
                results["blacklist_details"] = blacklist_data

            # Procesar resultado de ofertas activas
            if isinstance(offers_response, requests.Response):
                offers_response.raise_for_status()
                offers_data = offers_response.json()
                results["active_offers_check"] = offers_data.get('mensaje') if offers_data.get('mensaje') else "Tiene activo"
                results["offers_details"] = offers_data

            if isinstance(renapo_response, requests.Response):
                renapo_response.raise_for_status()
                renapo_data = renapo_response.json()
                results["active_renapo_check"] = renapo_data.get('mensaje') if renapo_data.get('mensaje') else "no es CURP valida."
                results["renapo_details"] = renapo_data

            # Determinar si puede continuar
            can_proceed: bool = (
                results["blacklist_check"] == "NoEncontrado_CURP" and
                results["active_offers_check"] == "Validacion de ofertas activas exitosa" and 
                results["active_renapo_check"] == "CURP válido"
            )

            results["can_proceed"] = can_proceed
            results["message"] = "Validación completada" if can_proceed else "CURP no válido para proceso"

            return results

        except Exception as e:
            error_msg = f"Error validando CURP: {e}"
            print(error_msg)
            return {
                "status": "error",
                "message": error_msg,
                "curp": curp
            }

    async def submit_form_data(self, tool_context: ToolContext, additional_data: dict) -> dict:
        """
        Envía los datos del formulario completo al API.

        Args:
            additional_data: Datos adicionales del usuario (celular, email, ingresos, etc.)

        Returns:
            Dict con resultado del envío
        """
        try:
            user_data = tool_context.state.get('user_data', {})
            if not user_data:
                return {
                    "status": "error",
                    "message": "Datos de usuario no disponibles. Procesa INE primero."
                }

            flow_uuid = tool_context.state.get('flow_uuid')
            if not flow_uuid:
                return {
                    "status": "error",
                    "message": "Flujo no inicializado"
                }
            
            # Combinar datos del INE con datos adicionales
            form_data = {
                "celular": additional_data.get('celular'),
                "curp": user_data.get('curp'),
                "primerNombre": user_data.get('primerNombre'),
                "segundoNombre": user_data.get('segundoNombre'),
                "primerApellido": user_data.get('primerApellido'),
                "segundoApellido": user_data.get('segundoApellido'),
                "fechaNacimiento": user_data.get('fechaNacimiento'),
                "calle": user_data.get('calle'),
                "codigoPostal": "87904", # user_data.get('codigoPostal'),
                "rfc": user_data.get('rfc'),
                "correoElectronico": additional_data.get('correoElectronico'),
                "ingresoMensual": additional_data.get('ingresoMensual'),
                "precioMoto": additional_data.get('precioMoto'),
                "enganche": None,
                "numeroPromotor": "MAXIAGENT",
                "marcaMoto": additional_data.get('marcaMoto'),
                "modeloMoto": additional_data.get('modeloMoto'),
                "estado": "28", # additional_data.get('estado'),
                "municipio": "2035", # additional_data.get('municipio'),
                "colonia": "136710", # additional_data.get('colonia'),
                "fk_usuario_creacion": "",
                "mostrarCampos": None
            }

            # Validar datos requeridos
            required_fields = ['celular', 'curp', 'correoElectronico', 'ingresoMensual', 'precioMoto']
            missing_fields = [field for field in required_fields if not form_data.get(field)]

            if missing_fields:
                return {
                    "status": "error",
                    "message": f"Campos requeridos faltantes: {', '.join(missing_fields)}"
                }

            api_url = f"{current_config.URL_ORIGINADOR}/originacion/capturar-formulario"

            headers = {
                    'User-Agent': 'Python-HTTP-Post-Client/1.0',
                    'X-API-KEY': current_config.KEY_ORIGINADOR,
                }
            
            params: Dict[str, str] = {"uuidFlujo": flow_uuid}

            response = requests.post(
                api_url,
                params=params,
                json=form_data,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()

            # Guardar datos del formulario en estado
            tool_context.state['form_data'] = form_data

            return {
                "status": "success",
                "message": "Formulario enviado exitosamente",
                "form_data": form_data
            }

        except Exception as e:
            error_msg = f"Error enviando formulario: {e}"
            print(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }

    async def query_offers(self, tool_context: ToolContext, location_data: dict) -> dict:
        """
        Consulta ofertas de financiamiento disponibles.

        Args:
            location_data: Datos de ubicación (idMunicipio, idEstado, etc.)

        Returns:
            Dict con ofertas disponibles
        """
        try:
            form_data = tool_context.state.get('form_data')
            if not form_data:
                return {
                    "status": "error",
                    "message": "Datos del formulario no disponibles. Envía el formulario primero."
                }

            flow_uuid = tool_context.state.get('flow_uuid')
            if not flow_uuid:
                return {
                    "status": "error",
                    "message": "Flujo no inicializado"
                }
            
            # Preparar payload para consulta de ofertas
            offer_query = {
                "ingresoMensual": form_data.get('ingresoMensual'),
                "precioMoto": float(form_data.get('precioMoto', 0)),
                "garantia": None,
                "fechaNacimiento": form_data.get('fechaNacimiento'),
                "idMunicipio": location_data.get('idMunicipio'),
                "idEstado": location_data.get('idEstado'),
                "codigoPostal": form_data.get('codigoPostal'),
                "idSucursal": location_data.get('idSucursal', 1),
                "idDistribuidor": location_data.get('idDistribuidor', 1),
                "marcaMoto": form_data.get('marcaMoto'),
                "modeloMoto": form_data.get('modeloMoto'),
                "fechaHoraCreacionOferta": datetime.now().isoformat(),
                "idUsuarioCreacion": form_data.get('fk_usuario_creacion'),
                "idOferta": str(uuid.uuid4()),
                "idPais": location_data.get('idPais', 'MX')
            }

            api_url = f"{current_config.URL_ORIGINADOR}/originacion/consultar-ofertas"
            
            headers = {
                'User-Agent': 'Python-HTTP-Post-Client/1.0',
                'X-API-KEY': current_config.KEY_ORIGINADOR,
            }

            response = requests.post(
                api_url,
                json=offer_query,
                headers=headers,
                timeout=45
            )
            offers_data = response.json()

            print(f"offers_data {offers_data}")
            response.raise_for_status()

            # Guardar ofertas en estado
            tool_context.state['offers'] = offers_data

            return {
                "status": "success",
                "message": "Ofertas consultadas exitosamente",
                "offers": offers_data,
                "offer_count": len(offers_data.get('offers', []))
            }

        except Exception as e:
            error_msg = f"Error consultando ofertas: {e}"
            print(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }

    # === Validation Methods ===

    def validate_required_data(self, tool_context: ToolContext, step: str) -> dict:
        """
        Valida que los datos requeridos estén presentes para un paso específico.

        Args:
            step: Paso del flujo a validar ('flow_init', 'ine_process', 'form_submit', etc.)

        Returns:
            Dict con resultado de validación
        """
        state = tool_context.state

        validation_rules = {
            'flow_init': ['flow_uuid'],
            'ine_process': ['flow_uuid', 'ine_front_image', 'ine_back_image'],
            'ine_verify': ['flow_uuid', 'user_data'],
            'curp_validate': ['user_data'],
            'form_submit': ['user_data'],
            'offers_query': ['form_data']
        }

        required_fields = validation_rules.get(step, [])
        missing_fields = []

        for field in required_fields:
            if field not in state or not state[field]:
                missing_fields.append(field)

        is_valid = len(missing_fields) == 0

        return {
            "valid": is_valid,
            "step": step,
            "missing_fields": missing_fields,
            "message": "Validación exitosa" if is_valid else f"Campos faltantes: {', '.join(missing_fields)}"
        }

    def validate_curp_format(self, tool_context: ToolContext, curp: str) -> dict:
        """
        Valida el formato de un CURP mexicano.

        Args:
            curp: CURP a validar

        Returns:
            Dict con resultado de validación
        """
        import re

        if not curp:
            return {"valid": False, "message": "CURP no proporcionado"}

        # Patrón regex para CURP mexicano
        curp_pattern = r'^[A-Z]{4}[0-9]{6}[HM][A-Z]{5}[0-9A-Z]{2}$'

        is_valid = bool(re.match(curp_pattern, curp.upper()))

        return {
            "valid": is_valid,
            "curp": curp.upper(),
            "message": "CURP válido" if is_valid else "Formato de CURP inválido"
        }

    def validate_rfc_format(self, tool_context: ToolContext, rfc: str) -> dict:
        """
        Valida el formato de un RFC mexicano.

        Args:
            rfc: RFC a validar

        Returns:
            Dict con resultado de validación
        """
        if not rfc:
            return {"valid": False, "message": "RFC no proporcionado"}

        # Patrón regex para RFC mexicano (persona física)
        rfc_pattern = r'^[A-Z]{4}[0-9]{6}[A-Z0-9]{3}$'

        is_valid = bool(re.match(rfc_pattern, rfc.upper()))

        return {
            "valid": is_valid,
            "rfc": rfc.upper(),
            "message": "RFC válido" if is_valid else "Formato de RFC inválido"
        }