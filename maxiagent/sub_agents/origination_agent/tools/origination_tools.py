from __future__ import annotations

import re
import asyncio
import logging
import requests

from requests.auth import HTTPBasicAuth
from typing import List, Dict, Any

from google.adk.tools.tool_context import ToolContext
from ....core import settings
from ....tools.base_tools import BaseAgentTools

from ....core import get_logger
logger: logging.Logger = get_logger(__name__)


class OriginationTools(BaseAgentTools):
    """Clase para gestionar las herramientas del agente de originación."""

    VALIDATION_ENDPOINTS = {
        'blacklist': {
            'url_path': '/originacion/validarCurpListaNegra',
            'check_key': 'blacklist_check',
            'details_key': 'blacklist_details',
            'default_message': 'Es lista negra',
            'success_value': 'NoEncontrado_CURP'
        },
        'offers': {
            'url_path': '/originacion/validarOfertasActivas',
            'check_key': 'active_offers_check',
            'details_key': 'offers_details',
            'default_message': 'Tiene activo',
            'success_value': 'Validacion de ofertas activas exitosa'
        },
        'renapo': {
            'url_path': '/originacion/validacion-curp',
            'check_key': 'active_renapo_check',
            'details_key': 'renapo_details',
            'default_message': 'no es CURP valida.',
            'success_value': 'CURP válido'
        }
    }

    def __init__(self):
        super().__init__()
        self._tools = {
            'chained_tools': {
                'process_ine_complete': self.process_ine_complete,
                'validate_curp_only': self.validate_curp_only,
                'complete_form_and_nip': self.complete_form_and_nip,
                'confirm_nip_and_get_offers': self.confirm_nip_and_get_offers
            },
            'quotation_flow': {
                'initialize_flow': self.initialize_flow,
                'resend_nip': self.resend_nip,
                'select_offer': self.select_offer
            }
        }

    # === Chained Tools (Auto-execute multiple steps) ===

    async def process_ine_complete(self, tool_context: ToolContext) -> dict:
        """
        TOOL ENCADENADA: Ejecuta automáticamente los pasos 3-4 después del análisis de imágenes.

        Pasos que ejecuta:
        1. process_ine_documents() - Envía imágenes al API
        2. verify_ine_processing() - Verifica y obtiene datos del INE
        3. validate_curp() - Valida el CURP

        Returns:
            Dict con resultado final del proceso completo
        """
        logger.info("🔗 Iniciando proceso completo de INE (pasos 3-4)")

        try:
            # Paso 3a: Procesar documentos INE
            logger.info("📤 Paso 3a: Procesando documentos INE...")
            process_result = await self._process_ine_documents(tool_context)

            if process_result.get('status') != 'success':
                # Pasar toda la información de error incluyendo detalles del análisis
                return {
                    "status": "error",
                    "step": "process_ine_documents",
                    "message": f"Fallo en procesamiento INE: {process_result.get('message')}",
                    "missing_images": process_result.get('missing_images', []),
                    "analysis_errors": process_result.get('analysis_errors', []),
                    "processing_metadata": process_result.get('processing_metadata', {}),
                    "suggestion": "Solicita al usuario que envíe las imágenes faltantes con una explicación clara de por qué fallaron."
                }

            # Paso 3b: Verificar procesamiento
            logger.info("🔍 Paso 3b: Verificando procesamiento INE...")
            verify_result = await self._verify_ine_processing(tool_context)

            if verify_result.get('status') != 'success':
                return {
                    "status": "error",
                    "step": "verify_ine_processing",
                    "message": f"Fallo en verificación INE: {verify_result.get('message')}"
                }

            # Paso 4: Validar CURP
            logger.info("✅ Paso 4: Validando CURP...")
            curp_result = await self._validate_curp(tool_context)

            if curp_result.get('status') != 'success':
                return {
                    "status": "error",
                    "step": "validate_curp",
                    "message": f"Fallo en validación CURP: {curp_result.get('message')}"
                }

            logger.info("✨ Proceso completo de INE finalizado exitosamente")

            return {
                "status": "success",
                "message": "Datos del INE procesados y CURP validado exitosamente",
                "user_data": tool_context.state.get('user_data', {}),
                "next_step": "Ahora necesito que me proporciones: celular, correo electrónico, marca de la moto y precio de la moto."
            }

        except Exception as e:
            logger.error(f"Error en proceso completo de INE: {e}")
            return {
                "status": "error",
                "message": f"Error inesperado en proceso de INE: {str(e)}"
            }

    async def validate_curp_only(self, tool_context: ToolContext, curp: str) -> dict:
        """
        TOOL ENCADENADA: Valida CURP directamente sin requerir INE.

        Esta tool permite continuar el proceso de cotización usando solo CURP,
        saltando completamente el procesamiento de documentos INE.

        Pasos que ejecuta:
        1. Valida formato de CURP
        2. Valida CURP contra lista negra, ofertas activas y RENAPO
        3. Obtiene datos personales de RENAPO (nombre, apellidos, fecha nacimiento, RFC)
        4. Guarda los datos en el estado para uso posterior

        Args:
            curp: CURP de 18 caracteres del usuario

        Returns:
            Dict con resultado de la validación y datos obtenidos de RENAPO
        """
        logger.info("🔗 Iniciando validación solo con CURP (sin INE)")

        try:
            # Validar que existe flow_uuid
            flow_uuid = tool_context.state.get('flow_uuid')
            if not flow_uuid:
                return {
                    "status": "error",
                    "message": "Flujo no inicializado. Ejecuta initialize_flow primero."
                }

            # Paso 1: Validar formato de CURP
            logger.info("📝 Paso 1: Validando formato de CURP...")
            format_validation = self._validate_curp_format(curp)

            if not format_validation.get('valid', False):
                return {
                    "status": "error",
                    "step": "format_validation",
                    "message": f"Formato de CURP inválido: {format_validation.get('message')}"
                }

            curp_upper = curp.upper()

            # Paso 2: Validar CURP (lista negra, ofertas activas, RENAPO)
            logger.info("✅ Paso 2: Validando CURP contra servicios externos...")

            # Crear user_data temporal solo con CURP para la validación
            tool_context.state['user_data'] = {'curp': curp_upper}

            curp_result = await self._validate_curp(tool_context)

            if curp_result.get('status') != 'success':
                return {
                    "status": "error",
                    "step": "validate_curp",
                    "message": f"Fallo en validación CURP: {curp_result.get('message')}"
                }

            if not curp_result.get('can_proceed', False):
                return {
                    "status": "error",
                    "step": "validate_curp",
                    "message": "CURP no válido para continuar el proceso",
                    "details": {
                        "blacklist_check": curp_result.get('blacklist_check'),
                        "active_offers_check": curp_result.get('active_offers_check'),
                        "renapo_check": curp_result.get('active_renapo_check')
                    }
                }

            # Paso 3: Extraer datos de RENAPO
            logger.info("📋 Paso 3: Extrayendo datos personales de RENAPO...")
            renapo_details = curp_result.get('renapo_details', {})
            renapo_response = renapo_details.get('responseRenapoDto', {})

            # Construir user_data con información de RENAPO
            user_data = {
                'curp': curp_upper,
                'primerNombre': renapo_response.get('primer_nombre', ''),
                'segundoNombre': renapo_response.get('segundo_nombre', ''),
                'apellidoPaterno': renapo_response.get('apellido_paterno', ''),
                'apellidoMaterno': renapo_response.get('apellido_materno', ''),
                'fechaNacimiento': renapo_response.get('fecha_nacimiento', ''),
                'rfc': renapo_response.get('rfc', ''),
                'validation_method': 'curp_only'  # Marcar que se validó solo con CURP
            }

            # Guardar en estado
            tool_context.state['user_data'] = user_data
            tool_context.state['curp_only_mode'] = True  # Flag para indicar que NO hay INE

            logger.info("Validación con CURP completada exitosamente")

            return {
                "status": "success",
                "message": "CURP validado exitosamente",
                "user_data": user_data,
                "next_step": "Ahora necesito que me proporciones: celular, correo electrónico, marca de la moto, precio de la moto, código postal (5 dígitos) y tu dirección (calle y número)."
            }

        except Exception as e:
            logger.error(f"Error en validación solo con CURP: {e}")
            return {
                "status": "error",
                "message": f"Error inesperado en validación de CURP: {str(e)}"
            }

    async def complete_form_and_nip(self, tool_context: ToolContext, additional_data: dict) -> dict:
        """
        TOOL ENCADENADA: Ejecuta automáticamente los pasos 5-6 (formulario + NIP).

        Pasos que ejecuta:
        1. submit_form_data() - Envía formulario con datos adicionales
        2. send_nip() - Solicita envío de NIP automáticamente

        Args:
            additional_data: Dict con {celular, correoElectronico, marcaMoto, precioMoto, ...}

        Returns:
            Dict con resultado y mensaje para solicitar NIP al usuario
        """
        logger.info("🔗 Iniciando proceso de formulario + solicitud NIP (pasos 5-6)")

        try:
            # Paso 5: Enviar formulario
            logger.info("📝 Paso 5: Enviando formulario...")
            form_result = await self._submit_form_data(tool_context, additional_data)

            if form_result.get('status') != 'success':
                return {
                    "status": "error",
                    "step": "submit_form_data",
                    "message": f"Fallo en envío de formulario: {form_result.get('message')}"
                }

            # Paso 6: Solicitar NIP automáticamente
            logger.info("📱 Paso 6: Solicitando envío de NIP...")
            nip_result = await self._send_nip(tool_context)

            if nip_result.get('status') != 'success':
                return {
                    "status": "error",
                    "step": "send_nip",
                    "message": f"Fallo en solicitud de NIP: {nip_result.get('message')}"
                }
            
            nip_requested = tool_context.state['nip_requested']

            if nip_requested:
                logger.info("✨ Formulario enviado y NIP solicitado exitosamente")
                msg: str = "✅ Formulario enviado exitosamente\n\n📱 He solicitado el envío de un NIP de 6 dígitos a tu celular.\n\n⏱️ Por favor, revisa tu teléfono y proporciónameEL NIP cuando lo recibas."
            else: 
                logger.info("✨ Formulario enviado, no es necesario solicitar NIP")
                msg: str = "✅ Formulario enviado exitosamente\n\n📱 Ahora voy a darte tus ofertas."
            
            return {
                "status": "success",
                "message": msg,
                "next_step": "Esperando NIP del usuario" if nip_requested else "Pasando al siguiente paso."
            }

        except Exception as e:
            logger.error(f"Error en proceso de formulario + NIP: {e}")
            return {
                "status": "error",
                "message": f"Error inesperado: {str(e)}"
            }

    async def confirm_nip_and_get_offers(self, tool_context: ToolContext, nip: str = "") -> dict:
        """
        TOOL ENCADENADA: Ejecuta automáticamente los pasos 7-8 (confirmar NIP + consultar ofertas).

        Pasos que ejecuta:
        1. confirm_nip() - Confirma el NIP de 6 dígitos (solo si fue requerido)
        2. query_offers() - Consulta ofertas automáticamente

        Args:
            nip: NIP de 6 dígitos proporcionado por el usuario (opcional si no fue requerido)

        Returns:
            Dict con ofertas disponibles formateadas
        """
        logger.info("🔗 Iniciando confirmación NIP + consulta de ofertas (pasos 7-8)")

        try:
            nip_requested = tool_context.state.get('nip_requested', False)

            # Paso 7: Confirmar NIP (solo si fue requerido)
            if nip_requested:
                logger.info("🔐 Paso 7: Confirmando NIP...")
                nip_result = await self._confirm_nip(tool_context, nip)

                if nip_result.get('status') != 'success':
                    return {
                        "status": "error",
                        "step": "confirm_nip",
                        "message": f"Fallo en confirmación de NIP: {nip_result.get('message')}"
                    }
            else:
                # Si no se requirió NIP, marcar como confirmado para continuar el flujo
                logger.info("⏭️ Paso 7: NIP no requerido, saltando confirmación...")
                tool_context.state['nip_confirmed'] = True

            # Paso 8: Consultar ofertas automáticamente
            logger.info("💰 Paso 8: Consultando ofertas...")
            offers_result = await self._query_offers(tool_context)

            if offers_result.get('status') != 'success':
                return {
                    "status": "error",
                    "step": "query_offers",
                    "message": f"Fallo en consulta de ofertas: {offers_result.get('message')}"
                }

            success_message = "✅ NIP confirmado exitosamente" if nip_requested else "✅ Proceso completado exitosamente"
            logger.info(f"✨ {'NIP confirmado y ofertas consultadas' if nip_requested else 'Ofertas consultadas'} exitosamente")

            return {
                "status": "success",
                "message": success_message,
                "offers": offers_result.get('offers', []),
                "offers_count": offers_result.get('offers_count', 0),
                "next_step": "Presenta las ofertas al usuario usando el formato obligatorio"
            }

        except Exception as e:
            logger.error(f"Error en confirmación NIP + ofertas: {e}")
            return {
                "status": "error",
                "message": f"Error inesperado: {str(e)}"
            }

    # === Quotation Flow Methods ===

    async def initialize_flow(self, tool_context: ToolContext) -> dict:
        """
        Inicializa el flujo de cotización obteniendo un UUID único.

        Returns:
            Dict con el UUID del flujo o error
        """
        logger.info("Iniciando nuevo flujo de cotización")
        try:
            api_url = f"{settings.URL_ORIGINADOR}/originacion/nuevo-flujo"
            logger.debug(f"Llamando a API: {api_url}")

            response = await self._call_originador_api(api_url, method='GET')

            data = response.json()
            flow_uuid = data.get('uuidFlujo')

            if not flow_uuid:
                logger.error("El servidor no retornó un flow_uuid válido")
                raise ValueError("No se recibió flow_uuid del servidor")

            # Guardar en estado de sesión
            tool_context.state['flow_uuid'] = flow_uuid
            logger.info(f"Flujo inicializado exitosamente con UUID: {flow_uuid}")

            result = {
                "status": "success",
                "message": f"Flujo inicializado exitosamente."
            }
            logger.debug(f"Retornando resultado: {result}")
            return result

        except requests.RequestException as e:
            error_msg = self._handle_request_exception(e, "inicializar flujo")
            logger.error(f"Error de request inicializando flujo: {error_msg}")
            result = {
                "status": "error",
                "message": error_msg
            }
            logger.debug(f"Retornando error: {result}")
            return result
        except Exception as e:
            error_msg = f"Error inesperado inicializando flujo: {e}"
            logger.error(error_msg, exc_info=True)
            result = {
                "status": "error",
                "message": error_msg
            }
            logger.debug(f"Retornando error: {result}")
            return result

    async def _process_ine_documents(self, tool_context: ToolContext) -> dict:
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
            ine_front: str | None = tool_context.state.get('ine_front_image')
            ine_back: str | None = tool_context.state.get('ine_back_image')

            # Obtener metadata de errores del análisis de imágenes
            analysis_errors = tool_context.state.get('ine_analysis_errors', [])
            processing_metadata = tool_context.state.get('ine_processing_metadata', {})

            # Logging crítico del estado
            logger.info("📤 Preparando envío de INE al API")
            logger.debug(f"Estado de imágenes - flow_uuid: {flow_uuid}")
            logger.debug(f"INE frontal: {'presente' if ine_front else 'FALTANTE'} ({len(ine_front) if ine_front else 0} chars)")
            logger.debug(f"INE reverso: {'presente' if ine_back else 'FALTANTE'} ({len(ine_back) if ine_back else 0} chars)")
            if analysis_errors:
                logger.warning(f"Se detectaron {len(analysis_errors)} errores de análisis previos")

            if ine_front and ine_back:
                api_url: str = f"{settings.URL_ORIGINADOR}/originacion/subir-ine"
                params: Dict[str, str] = {"uuidFlujo": flow_uuid}

                payload: Dict[str, str] = {
                    "frenteBase64": ine_front,
                    "reversoBase64": ine_back
                }

                logger.info(f"🚀 Enviando imágenes INE al API - URL: {api_url}")
                response = await self._call_originador_api(
                    api_url,
                    method='POST',
                    params=params,
                    json_data=payload,
                    timeout=60
                )

                logger.info(f"✅ API respondió exitosamente - Status: {response.status_code}")

                result = {
                    "status": "success",
                    "message": "Documentos INE enviados para procesamiento"
                }
                logger.debug(f"Retornando resultado exitoso: {result}")
                return result

            missing_images = []
            error_details = []

            if not ine_front:
                missing_images.append("frente")
                # Buscar errores relacionados con imagen frontal
                front_errors = [err for err in analysis_errors if err.get('error_type') in ['analysis_failed', 'type_indeterminate']]
                if front_errors:
                    error_details.append(f"Imagen frente: {front_errors[0].get('error_message', 'Error desconocido')}")

            if not ine_back:
                missing_images.append("reverso")
                # Buscar errores relacionados con imagen reverso
                back_errors = [err for err in analysis_errors if err.get('error_type') in ['analysis_failed', 'type_indeterminate']]
                if back_errors and len(back_errors) > (1 if not ine_front else 0):
                    error_details.append(f"Imagen reverso: {back_errors[-1].get('error_message', 'Error desconocido')}")

            missing_text = " y ".join(missing_images)
            logger.error(f"❌ Faltan imágenes del INE: {missing_text}")
            logger.debug(f"Estado - Frontal: {bool(ine_front)}, Reverso: {bool(ine_back)}")

            # Construir mensaje con detalles de errores
            error_message = f"Se requieren ambas imágenes del INE. Faltante(s): {missing_text}."

            if error_details:
                logger.warning(f"Detalles de errores: {error_details}")
                error_message += "\n\nPosibles causas:\n" + "\n".join([f"• {detail}" for detail in error_details])
            else:
                error_message += " Por favor, proporciona la(s) imagen(es) faltante(s)."

            # Agregar información de metadata si está disponible
            if processing_metadata:
                total_received = processing_metadata.get('total_images_received', 0)
                if total_received > 0:
                    logger.warning(f"Se recibieron {total_received} imagen(es) pero no se clasificaron correctamente")
                    error_message += f"\n\nSe recibieron {total_received} imagen(es) pero no se pudieron clasificar correctamente."

            result = {
                "status": "error",
                "message": error_message,
                "missing_images": missing_images,
                "has_front": bool(ine_front),
                "has_back": bool(ine_back),
                "analysis_errors": analysis_errors,
                "processing_metadata": processing_metadata
            }
            logger.debug(f"Retornando error de imágenes faltantes: {result['message']}")
            return result

        except requests.RequestException as e:
            error_msg = self._handle_request_exception(e, "procesar documentos INE")
            logger.error(f"Error de request procesando INE: {error_msg}")
            result = {
                "status": "error",
                "message": error_msg
            }
            logger.debug(f"Retornando error de request: {result}")
            return result
        except Exception as e:
            error_msg = f"Error inesperado procesando documentos INE: {e}"
            logger.error(error_msg, exc_info=True)
            result = {
                "status": "error",
                "message": error_msg
            }
            logger.debug(f"Retornando error inesperado: {result}")
            return result

    async def _verify_ine_processing(self, tool_context: ToolContext, max_retries: int = 10) -> dict:
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
            
            api_url = f"{settings.URL_ORIGINADOR}/originacion/estatus-ine"
            params = {"uuidFlujo": flow_uuid}

            for attempt in range(max_retries):
                try:
                    response = await self._call_originador_api(
                        api_url,
                        method='GET',
                        params=params,
                        timeout=30
                    )
                    
                    # Validar que sea JSON válido
                    try:
                        data = response.json()
                    except ValueError:
                        raise requests.RequestException("Respuesta no es JSON válido")
                    
                    completado: bool = data.get('completado', False)
                    
                    if completado:
                        # Procesamiento completado, preparar respuesta exitosa
                        form_data = data.get('formularioCaptura', {})
                        tool_context.state['user_data'] = form_data
                        return {
                            "status": "success",
                            "completed": True,
                            "user_data": form_data,
                            "message": "Procesamiento completado exitosamente"
                        }
                    
                    # No completado, esperar antes del siguiente intento
                    if attempt < max_retries - 1:  # No esperar en el último intento
                        await asyncio.sleep(0.5)
                            
                except requests.RequestException as e:
                    if attempt == max_retries - 1:
                        raise e
                    await asyncio.sleep(1)
            
            # Si llegamos aquí, se agotaron los intentos
            return {
                "status": "timeout",
                "message": f"El procesamiento no se completó después de {max_retries} intentos"
            }

        except Exception as e:
            error_msg = f"Error verificando procesamiento INE: {e}"
            logger.error(error_msg, exc_info=True)
            result = {
                "status": "error",
                "message": error_msg
            }
            logger.debug(f"Retornando error: {result}")
            return result

    async def _validate_curp(self, tool_context: ToolContext) -> dict:
        """
        Valida CURP contra lista negra y ofertas activas.

        Returns:
            Dict con resultado de validaciones
        """
        try:
            # Validaciones iniciales
            user_data: dict = tool_context.state.get('user_data', {})
            if not user_data:
                return {
                    "status": "error",
                    "message": "Datos de usuario no disponibles. Procesa INE primero."
                }
            
            curp: str | None = user_data.get('curp', None)
            if not curp:
                return {
                    "status": "error",
                    "message": "CURP faltante en el contexto actual."
                }

            validation: dict = self._validate_curp_format(curp)
            if not validation.get('valid', False):
                return {
                    "status": "error",
                    "message": "El formato de la CURP no es válido."
                }

            flow_uuid = tool_context.state.get('flow_uuid')
            if not flow_uuid:
                return {
                    "status": "error",
                    "message": "Flujo no inicializado."
                }
            
            api_base: str | None = settings.URL_ORIGINADOR
            if not api_base:
                return {
                    "status": "error",
                    "message": "No hay API para consultar."
                }

            # Ejecutar validaciones en paralelo
            responses = await self._execute_parallel_validations(curp, flow_uuid, api_base)

            # Inicializar resultados
            results: Dict[str, str | bool] = {
                "status": "success",
                "curp": curp,
                "can_proceed": False
            }
            
            # Procesar todas las respuestas usando la configuración
            response_data = {}
            for response, (endpoint_name, config) in zip(responses, self.VALIDATION_ENDPOINTS.items()):
                results[config['check_key']] = "error"

                data = self._process_api_response(response, results, config)
                response_data[endpoint_name] = data

            # Determinar si puede continuar usando la configuración
            can_proceed: bool = all(
                                    results[config['check_key']] == config['success_value']
                                    for config in self.VALIDATION_ENDPOINTS.values()
                                )
            
            results["can_proceed"] = can_proceed
            results["message"] = "Validación completada" if can_proceed else "CURP no válido para proceso"
            # Guardar datos de las validaciones de curp
            tool_context.state['curp_results'] = results

            return results

        except Exception as e:
            return {
                "status": "error",
                "message": f"Error durante validación: {str(e)}"
            }

    async def _submit_form_data(self, tool_context: ToolContext, additional_data: dict) -> dict:
        """
        Envía los datos del formulario completo al API.

        Args:
            additional_data: Datos adicionales del usuario (celular, email, y dirección si es modo CURP-only)

        Returns:
            Dict con resultado del envío
        """
        try:
            user_data: dict = tool_context.state.get('user_data', {})
            if not user_data:
                return {
                    "status": "error",
                    "message": "Datos de usuario no disponibles. Procesa INE o valida CURP primero."
                }

            flow_uuid: str = tool_context.state.get('flow_uuid')
            if not flow_uuid:
                return {
                    "status": "error",
                    "message": "Flujo no inicializado"
                }

            # Detectar si estamos en modo CURP-only (sin INE)
            curp_only_mode = tool_context.state.get('curp_only_mode', False)

            # Obtener código postal
            if curp_only_mode:
                # En modo CURP-only, el código postal viene de additional_data
                codigoPostal = additional_data.get('codigoPostal')
                if not codigoPostal:
                    return {
                        "status": "error",
                        "message": "Código postal es requerido. Por favor proporciona tu código postal."
                    }
            else:
                # En modo con INE, el código postal viene de user_data
                codigoPostal = user_data.get('codigoPostal')
                if not codigoPostal:
                    return {
                        "status": "error",
                        "message": "Código postal no disponible en los datos del INE"
                    }

            # Obteniendo los datos de dirección
            address_data: dict = self._get_address_data(codigoPostal)

            # En ocasiones, el OCR no puede obtener le fecha de nacimiento, entonces se obtiene
            # del resultado de renapo
            curp_results = tool_context.state.get('curp_results', {})
            renapo_details = curp_results.get('renapo_details', {})
            res_renapo = renapo_details.get('responseRenapoDto', {})
            
            # Obteniendo los datos personaes de renapo
            fecha_nacimiento = res_renapo.get('fecha_nacimiento')
            apellido_paterno = res_renapo.get('apellido_paterno')
            apellido_materno = res_renapo.get('apellido_materno')
            primer_nombre = res_renapo.get('primer_nombre')
            segundo_nombre = res_renapo.get('segundo_nombre')
            rfc = res_renapo.get('rfc')
            curp = res_renapo.get('curp')

            # Validar que se obtuvieron los datos de dirección correctamente
            if not address_data.get('success', False):
                error_msg = address_data.get('error', 'Error desconocido obteniendo datos de dirección')
                return {
                    "status": "error",
                    "message": f"No se pudieron obtener los datos de dirección: {error_msg}"
                }

            # Combinar datos según el modo (INE o CURP-only)
            if curp_only_mode:
                # En modo CURP-only, el usuario proporciona obligatoriamente:
                # - direccion (calle y número)
                # - codigoPostal (5 dígitos)
                # - celular, email, precioMoto
                # Y el sistema obtiene automáticamente de SEPOMEX:
                # - IDs: idEstado, idMunicipio, idColonia
                # - Nombres: estado (descripcionEstado), municipio, colonia
                form_data = {
                    "primerNombre": primer_nombre,
                    "segundoNombre": segundo_nombre,
                    "apellidoPaterno": apellido_paterno,
                    "apellidoMaterno": apellido_materno,
                    "fechaNacimiento": fecha_nacimiento,
                    "curp": curp,
                    "rfc": rfc,
                    "direccion": additional_data.get('direccion', ''),

                    "idColoniaPoblacion": address_data.get("idColonia"),
                    "coloniaPoblacion": address_data.get("colonia", ''),

                    "idAlcaldiaMunicipio": address_data.get("idMunicipio"),
                    "delegacionMunicipio": address_data.get("municipio", ''),

                    "idEstado": address_data.get("idEstado"),
                    "estado": address_data.get("estado", ''),

                    "ciudad": address_data.get("municipio", ''),  # Usamos municipio como ciudad

                    "codigoPostal": codigoPostal,

                    "email": additional_data.get('correoElectronico'),
                    "celular": additional_data.get('celular'),

                    "modeloMoto": additional_data.get('modeloMoto', ''),
                    "marcaMoto": additional_data.get('marcaMoto', ''),
                    "precioMoto": additional_data.get('precioMoto'),

                    "numeroPromotor": "MaxiAgent"
                }
            else:
                # En modo con INE, los datos de dirección vienen de user_data (INE)
                form_data = {
                    "primerNombre": primer_nombre,
                    "segundoNombre": segundo_nombre,
                    "apellidoPaterno": apellido_paterno,
                    "apellidoMaterno": apellido_materno,
                    "fechaNacimiento": fecha_nacimiento,
                    "curp": curp,
                    "rfc": rfc,
                    "direccion": user_data.get('direccion'),

                    "idColoniaPoblacion": address_data.get("idColonia"),
                    "coloniaPoblacion": user_data.get('coloniaPoblacion'),

                    "idAlcaldiaMunicipio": address_data.get("idMunicipio"),
                    "delegacionMunicipio": user_data.get('delegacionMunicipio'),

                    "idEstado": address_data.get("idEstado"),
                    "estado": user_data.get('estado'),

                    "ciudad": user_data.get('ciudad'),

                    "codigoPostal": codigoPostal,

                    "email": additional_data.get('correoElectronico'),
                    "celular": additional_data.get('celular'),

                    "modeloMoto": additional_data.get('modeloMoto', ''),
                    "marcaMoto": additional_data.get('marcaMoto', ''),
                    "precioMoto": additional_data.get('precioMoto'),

                    "numeroPromotor": "MaxiAgent"
                }

            # Validar datos requeridos
            required_fields: List[str] = ['celular', 'curp', 'email', 'marcaMoto', 'precioMoto']
            missing_fields: List[str] = [field for field in required_fields if not form_data.get(field)]

            # Validar datos de dirección requeridos
            address_required_fields: List[str] = ['idEstado', 'idAlcaldiaMunicipio', 'idColoniaPoblacion']
            missing_address_fields: List[str] = [field for field in address_required_fields if not form_data.get(field)]

            all_missing_fields: List[str] = missing_fields + missing_address_fields

            if all_missing_fields:
                return {
                    "status": "error",
                    "message": f"Campos requeridos faltantes: {', '.join(all_missing_fields)}"
                }

            # Guardar datos del formulario en estado
            tool_context.state['form_data'] = form_data

            api_url = f"{settings.URL_ORIGINADOR}/originacion/capturar-formulario"
            params: Dict[str, str] = {"uuidFlujo": flow_uuid}

            offer_info: requests.Response = await self._call_originador_api(
                api_url,
                method='POST',
                params=params,
                json_data=form_data,
                timeout=30
            )

            return {
                "status": "success",
                "message": "Formulario enviado exitosamente",
                "form_data": form_data
            }

        except requests.RequestException as e:
            error_msg = self._handle_request_exception(e, "enviar formulario")
            logger.error(f"Error de request enviando formulario: {error_msg}")
            result = {
                "status": "error",
                "message": error_msg
            }
            logger.debug(f"Retornando error: {result}")
            return result
        except Exception as e:
            error_msg = f"Error inesperado enviando formulario: {e}"
            logger.error(error_msg, exc_info=True)
            result = {
                "status": "error",
                "message": error_msg
            }
            logger.debug(f"Retornando error: {result}")
            return result

    async def _send_nip(self, tool_context: ToolContext) -> dict:
        """
        Solicita el envío de un NIP al usuario.

        Returns:
            Dict con resultado del envío del NIP
        """
        try:
            flow_uuid = tool_context.state.get('flow_uuid')
            if not flow_uuid:
                return {
                    "status": "error",
                    "message": "Flujo no inicializado. Ejecuta initialize_flow primero."
                }

            # Verificar que se haya enviado el formulario
            form_data = tool_context.state.get('form_data')
            if not form_data:
                return {
                    "status": "error",
                    "message": "Formulario no enviado. Ejecuta submit_form_data primero."
                }

            api_url = f"{settings.URL_ORIGINADOR}/originacion/pedir-nip"
            params = {"uuidFlujo": flow_uuid}

            response: requests.Response = await self._call_originador_api(
                api_url,
                method='GET',
                params=params,
                timeout=30
            )

            response_json = response.json()

            logger.debug(f"Respuesta de pedir NIP: {response_json}")

            req_nip: bool = response_json.get("pedirNip")

            if req_nip:
                # Guardar estado del NIP
                tool_context.state['nip_requested'] = True
                logger.info("NIP solicitado - El usuario debe recibirlo en su celular")
            else:
                tool_context.state['nip_requested'] = False
                logger.info("NIP NO requerido - Saltando paso de confirmación")

            result = {
                "status": "success",
                "message": "NIP enviado exitosamente. El usuario debe revisar su teléfono celular." if req_nip else "No es necesario que pidas el NIP, al siguiente paso"
            }
            logger.debug(f"Retornando resultado: {result}")
            return result

        except requests.RequestException as e:
            error_msg = self._handle_request_exception(e, "enviar NIP")
            logger.error(f"Error de request enviando NIP: {error_msg}")
            result = {
                "status": "error",
                "message": error_msg
            }
            logger.debug(f"Retornando error: {result}")
            return result
        except Exception as e:
            error_msg = f"Error inesperado enviando NIP: {e}"
            logger.error(error_msg, exc_info=True)
            result = {
                "status": "error",
                "message": error_msg
            }
            logger.debug(f"Retornando error: {result}")
            return result

    async def _confirm_nip(self, tool_context: ToolContext, nip: str) -> dict:
        """
        Confirma el NIP ingresado por el usuario.

        Args:
            nip: NIP de 6 dígitos ingresado por el usuario

        Returns:
            Dict con resultado de la confirmación del NIP
        """
        try:
            flow_uuid = tool_context.state.get('flow_uuid')
            if not flow_uuid:
                return {
                    "status": "error",
                    "message": "Flujo no inicializado. Ejecuta initialize_flow primero."
                }

            # Verificar que se haya solicitado el NIP
            nip_requested = tool_context.state.get('nip_requested', False)
            if not nip_requested:
                return {
                    "status": "error",
                    "message": "NIP no solicitado. Ejecuta send_nip primero."
                }

            # Validar formato del NIP
            if not nip or len(nip) != 6 or not nip.isdigit():
                return {
                    "status": "error",
                    "message": "NIP debe ser un número de 6 dígitos."
                }

            api_url = f"{settings.URL_ORIGINADOR}/originacion/confirmar-nip"
            params = {
                "uuidFlujo": flow_uuid,
                "nip": nip
            }

            await self._call_originador_api(
                api_url,
                method='GET',
                params=params,
                timeout=30
            )

            # Guardar estado de NIP confirmado
            tool_context.state['nip_confirmed'] = True

            return {
                "status": "success",
                "message": "NIP confirmado exitosamente. Puedes proceder a consultar ofertas."
            }

        except requests.RequestException as e:
            error_msg = self._handle_request_exception(e, "confirmar NIP")
            logger.error(f"Error de request confirmando NIP: {error_msg}")
            result = {
                "status": "error",
                "message": error_msg
            }
            logger.debug(f"Retornando error: {result}")
            return result
        except Exception as e:
            error_msg = f"Error inesperado confirmando NIP: {e}"
            logger.error(error_msg, exc_info=True)
            result = {
                "status": "error",
                "message": error_msg
            }
            logger.debug(f"Retornando error: {result}")
            return result

    async def resend_nip(self, tool_context: ToolContext) -> dict:
        """
        Reenvía el NIP al usuario.

        Returns:
            Dict con resultado del reenvío del NIP
        """
        try:
            flow_uuid = tool_context.state.get('flow_uuid')
            if not flow_uuid:
                return {
                    "status": "error",
                    "message": "Flujo no inicializado. Ejecuta initialize_flow primero."
                }

            # Verificar que se haya solicitado el NIP previamente
            nip_requested = tool_context.state.get('nip_requested', False)
            if not nip_requested:
                return {
                    "status": "error",
                    "message": "Debes solicitar un NIP primero usando send_nip."
                }

            api_url = f"{settings.URL_ORIGINADOR}/originacion/reenviar-nip"
            params = {"uuidFlujo": flow_uuid}

            await self._call_originador_api(
                api_url,
                method='GET',
                params=params,
                timeout=30
            )

            return {
                "status": "success",
                "message": "NIP reenviado exitosamente. El usuario debe revisar su teléfono celular."
            }

        except requests.RequestException as e:
            error_msg = self._handle_request_exception(e, "reenviar NIP")
            logger.error(f"Error de request reenviando NIP: {error_msg}")
            result = {
                "status": "error",
                "message": error_msg
            }
            logger.debug(f"Retornando error: {result}")
            return result
        except Exception as e:
            error_msg = f"Error inesperado reenviando NIP: {e}"
            logger.error(error_msg, exc_info=True)
            result = {
                "status": "error",
                "message": error_msg
            }
            logger.debug(f"Retornando error: {result}")
            return result

    async def _query_offers(self, tool_context: ToolContext) -> dict:
        """
        Consulta ofertas de financiamiento disponibles.

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

            # Verificar que el NIP haya sido confirmado (solo si fue requerido)
            nip_requested = tool_context.state.get('nip_requested', False)
            nip_confirmed = tool_context.state.get('nip_confirmed', False)

            # Solo validar NIP si fue requerido
            if nip_requested and not nip_confirmed:
                return {
                    "status": "error",
                    "message": "NIP no confirmado. Confirma el NIP usando confirm_nip primero."
                }

            api_url = f"{settings.URL_ORIGINADOR}/originacion/consultar-ofertas"
            params = {
                "uuidFlujo": flow_uuid
            }

            response: requests.Response = await self._call_originador_api(
                api_url,
                method='GET',
                params=params,
                timeout=45
            )
            offers_data = response.json()

            # Guardar ofertas en estado
            tool_context.state['offers'] = offers_data

            return {
                "status": "success",
                "message": "Ofertas consultadas exitosamente",
                "offers": offers_data,
                "offer_count": len(offers_data)
            }

        except requests.RequestException as e:
            error_msg = self._handle_request_exception(e, "consultar ofertas")
            logger.error(f"Error de request consultando ofertas: {error_msg}")
            result = {
                "status": "error",
                "message": error_msg
            }
            logger.debug(f"Retornando error: {result}")
            return result
        except Exception as e:
            error_msg = f"Error inesperado consultando ofertas: {e}"
            logger.error(error_msg, exc_info=True)
            result = {
                "status": "error",
                "message": error_msg
            }
            logger.debug(f"Retornando error: {result}")
            return result

    async def select_offer(self, tool_context: ToolContext, plazo_selected: str) -> dict:
        """
        Selecciona una oferta de financiamiento específica basada en el plazo elegido.

        Args:
            plazo_selected: Plazo en semanas de la oferta seleccionada

        Returns:
            Dict con resultado de la selección de oferta
        """
        try:
            # Validar parámetro de entrada
            if not plazo_selected:
                return {
                    "status": "error",
                    "message": "Plazo de la oferta es requerido para la selección"
                }

            # Validar que el plazo sea numérico
            try:
                plazo_int = int(plazo_selected)
                if plazo_int <= 0:
                    raise ValueError("Plazo debe ser mayor a 0")
            except ValueError:
                return {
                    "status": "error",
                    "message": "Plazo debe ser un número válido de semanas"
                }

            # Verificar estado del flujo
            flow_uuid = tool_context.state.get('flow_uuid')
            if not flow_uuid:
                return {
                    "status": "error",
                    "message": "Flujo no inicializado. Ejecuta initialize_flow primero."
                }

            # Verificar que se hayan consultado ofertas previamente
            offers = tool_context.state.get('offers')
            if not offers:
                return {
                    "status": "error",
                    "message": "No hay ofertas disponibles. Consulta ofertas usando query_offers primero."
                }

            # Verificar que el plazo seleccionado existe en las ofertas disponibles
            available_plazos = [str(offer.get('plazo', '')) for offer in offers if offer.get('plazo')]
            if plazo_selected not in available_plazos:
                msg = f"Plazo '{plazo_selected}' no está disponible en las ofertas consultadas. Plazos disponibles: {', '.join(available_plazos)}"
                logger.error(msg)
                return {
                    "status": "error",
                    "message": msg 
                }

            # Verificar que el NIP haya sido confirmado
            nip_confirmed = tool_context.state.get('nip_confirmed', False)
            if not nip_confirmed:
                return {
                    "status": "error",
                    "message": "NIP no confirmado. Confirma el NIP usando confirm_nip primero."
                }

            # Guardando plazo seleccionado
            tool_context.state['selected_plazo'] = plazo_selected

            # Realizar la selección de la oferta
            api_url = f"{settings.URL_ORIGINADOR}/originacion/seleccionar-oferta"
            params = {
                "uuidFlujo": flow_uuid,
                "plazo": plazo_selected
            }

            response: requests.Response = await self._call_originador_api(
                api_url,
                method='GET',
                params=params,
                timeout=45
            )

            selected_offer_data = response.json()
            del selected_offer_data['imagen_ofertabase64']

            tool_context.state['selected_offer_data'] = selected_offer_data

            # Obtener datos del estado para enviar a n8n
            user_data = tool_context.state.get('user_data', {})
            form_data = tool_context.state.get('form_data', {})

            curp = user_data.get('curp', '')
            celular = form_data.get('celular', '')
            email = form_data.get('email', '')
            primer_nombre = form_data.get('primerNombre', '')
            segundo_nombre = form_data.get('segundoNombre', '')
            primer_apellido = form_data.get('apellidoPaterno', '')
            segundo_apellido = form_data.get('apellidoMaterno', '')
            precio_moto = form_data.get('precioMoto', '')
            direccion_ine = form_data.get('direccion', '')

            # Convertir state a formato serializable
            serializable_state: Dict[str, Any] = {
                'flow_uuid': tool_context.state.get('flow_uuid', ''),
                'selected_plazo': tool_context.state.get('selected_plazo', ''),
                'user_data': user_data,
                'form_data': form_data,
                'nip_confirmed': tool_context.state.get('nip_confirmed', False),
                'nip_requested': tool_context.state.get('nip_requested', False),
                'offers': tool_context.state.get('offers', []),
                'ine_front_image': tool_context.state.get('ine_front_image', ''),
                'ine_back_image': tool_context.state.get('ine_back_image', '')
            }

            try:
                # Obtener session_id y user_id nativamente del ToolContext
                user_id = tool_context._invocation_context.session.user_id
                session_id = tool_context._invocation_context.session.id
                logger.info(f"Session info obtained from _invocation_context: user_id={user_id}, session_id={session_id}")
            except (AttributeError, KeyError) as e:
                # Fallback si no está disponible (ej: desarrollo local)
                conversation_metadata = tool_context.state.get('conversation_metadata', {})
                user_id = conversation_metadata.get('user_id', '')
                session_id = conversation_metadata.get('session_id', '')
                logger.warning(f"Using fallback for session info from state - _invocation_context not available: {e}")

            # Preparar payload para n8n
            flow_payload = {
                **selected_offer_data,
                "curp": curp,
                "celular": celular,
                "email": email,
                "flow_uuid": flow_uuid,
                "plazo": plazo_selected,
                "primer_nombre": primer_nombre,
                "segundo_nombre": segundo_nombre,
                "primer_apellido": primer_apellido,
                "segundo_apellido": segundo_apellido,
                "precio_moto": precio_moto,
                "state": serializable_state,
                "direccion_ine": direccion_ine,
                "url_seguimiento": f"{settings.AGENT_CHAT_URL}/{user_id}/{session_id}"
            }

            # Realizar POST a Workflows
            try:
                flow_url: str = f"{settings.API_MAXIKASH}/api/trigger-workflow"
                n8n_response: requests.Response = requests.post(
                    url=flow_url,
                    json=flow_payload,
                    timeout=30
                )

                if n8n_response.status_code == 202:
                    logger.info(f"Workflow n8n triggered successfully for CURP: {curp}")
                else:
                    logger.warning(f"n8n workflow returned status {n8n_response.status_code}. Response {n8n_response.json()}")

            except requests.RequestException as n8n_error:
                # No fallar si n8n falla, solo loggear
                logger.error(f"Error triggering n8n workflow: {n8n_error}")

            # Realizar obtención de sucursal más cercana con el Código Postal
            codigo_postal = form_data.get('codigoPostal', '')
            marca_moto = form_data.get('marcaMoto', '')
            if codigo_postal:
                # Obtención de código postal mediante la API de Google Maps
                logger.info(f"Obteniendo sucursal más cercana para código postal: {codigo_postal}")
                nearest_branch = self._get_nearest_branch(codigo_postal, marca_moto)
                tool_context.state['nearest_branch'] = nearest_branch
                logger.info(f"Sucursal más cercana obtenida: {nearest_branch}")
            else:
                logger.warning("Código postal no disponible en form_data, no se puede obtener sucursal más cercana")
                nearest_branch = {}

            return {
                "status": "success",
                "message": f"Oferta de {plazo_selected} semanas seleccionada exitosamente",
                "plazo": plazo_selected,
                "sucursal_mas_cercana": nearest_branch if nearest_branch else "Información de sucursal no disponible"
            }

        except requests.RequestException as e:
            error_msg = self._handle_request_exception(e, "seleccionar oferta")
            logger.error(f"Error de request seleccionando oferta: {error_msg}")
            result = {
                "status": "error",
                "message": error_msg
            }
            logger.debug(f"Retornando error: {result}")
            return result
        except Exception as e:
            error_msg = f"Error inesperado seleccionando oferta: {e}"
            logger.error(error_msg, exc_info=True)
            result = {
                "status": "error",
                "message": error_msg
            }
            logger.debug(f"Retornando error: {result}")
            return result

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

    # === Internal aux methods ===

    # Función centralizada para llamadas a la API de originación
    async def _call_originador_api(
        self,
        url: str,
        method: str = 'POST',
        params: dict = {},
        json_data: dict = {},
        timeout: int = 30
    ) -> requests.Response:
        """
        Función centralizada para llamadas HTTP a la API de originación.

        Args:
            url: URL completa de la API
            method: Método HTTP ('GET' o 'POST')
            params: Parámetros URL para GET o POST
            json_data: Datos JSON para POST
            timeout: Timeout en segundos

        Returns:
            requests.Response: Respuesta HTTP
        """
        headers = {
            'User-Agent': 'Python-HTTP-Post-Client/1.0',
            'X-API-KEY': settings.KEY_ORIGINADOR,
        }

        loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()

        def make_request() -> requests.Response:
            if method.upper() == 'GET':
                response = requests.get(url, params=params, headers=headers, timeout=timeout)
            else:  # POST
                response = requests.post(url, params=params, json=json_data, headers=headers, timeout=timeout)

            # Lanzar excepción para códigos HTTP de error
            response.raise_for_status()
            return response

        return await loop.run_in_executor(None, make_request)

    def _validate_curp_format(self, curp: str) -> dict:
        """
        Valida el formato de un CURP mexicano.

        Args:
            curp: CURP a validar

        Returns:
            Dict con resultado de validación
        """

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
    
    def _process_api_response(self, response, results: Dict, config: Dict) -> dict:
        """
        Procesa una respuesta de API y actualiza el diccionario de resultados.
        
        Args:
            response: La respuesta HTTP o excepción
            results: Diccionario donde almacenar los resultados
            config: Configuración del endpoint (keys, mensajes, etc.)
            
        Returns:
            dict or None: Los datos JSON de la respuesta o None si no es válida
        """
        if not isinstance(response, requests.Response):
            return {}
        
        response.raise_for_status()
        data = response.json()
        results[config['check_key']] = data.get('mensaje', config['default_message'])
        results[config['details_key']] = data
        return data

    async def _execute_parallel_validations(self, curp: str, flow_uuid: str, api_base: str) -> list:
        """
        Ejecuta todas las validaciones de CURP en paralelo.
        
        Args:
            curp: El CURP a validar
            flow_uuid: UUID del flujo
            api_base: URL base de la API
            
        Returns:
            Tuple con las respuestas de todas las validaciones
        """
        params = {"curp": curp, "uuidFlujo": flow_uuid}
        
        # Crear las tareas paralelas usando la configuración
        tasks = []
        for endpoint_config in self.VALIDATION_ENDPOINTS.values():
            url = f"{api_base}{endpoint_config['url_path']}"
            task = self._call_originador_api(url, method='POST', params=params)
            tasks.append(task)
        
        return await asyncio.gather(*tasks, return_exceptions=True)

    def _handle_request_exception(self, exception: requests.RequestException, operation: str) -> str:
        """
        Maneja excepciones de requests de manera granular y retorna mensajes específicos.

        Args:
            exception: La excepción de requests
            operation: Descripción de la operación que falló

        Returns:
            str: Mensaje de error específico para el usuario
        """
        if isinstance(exception, requests.exceptions.Timeout):
            return f"Timeout al {operation}. El servidor tardó demasiado en responder. Intenta nuevamente."

        elif isinstance(exception, requests.exceptions.ConnectionError):
            return f"Error de conexión al {operation}. Verifica tu conexión a internet."

        elif isinstance(exception, requests.exceptions.HTTPError):
            if exception.response is None:
                return f"Error HTTP al {operation}. No se pudo obtener el código de estado."

            status_code = exception.response.status_code

            # Intentar extraer mensaje de la API
            api_message = self._extract_api_error_message(exception.response)
            message_suffix = f" Mensaje de la API: {api_message}" if api_message else ""

            logger.warning(f"Error HTTP al {operation} - Status: {status_code}, Mensaje API: {api_message}")

            if status_code == 400:
                return f"Solicitud inválida al {operation}. Revisa los datos enviados.{message_suffix}"
            elif status_code == 401:
                return f"Error de autenticación al {operation}. Token o credenciales inválidas.{message_suffix}"
            elif status_code == 403:
                return f"Acceso denegado al {operation}. Permisos insuficientes.{message_suffix}"
            elif status_code == 404:
                return f"Servicio no encontrado al {operation}. El endpoint no existe.{message_suffix}"
            elif status_code == 409:
                return f"Conflicto al {operation}. Los datos ya existen o están en conflicto.{message_suffix}"
            elif status_code == 422:
                return f"Datos inválidos al {operation}. Revisa el formato de los datos.{message_suffix}"
            elif 500 <= status_code < 600:
                return f"Error interno del servidor al {operation}. Intenta nuevamente en unos minutos.{message_suffix}"
            else:
                return f"Error HTTP {status_code} al {operation}.{message_suffix}"

        elif isinstance(exception, requests.exceptions.RequestException):
            return f"Error en la solicitud al {operation}: {str(exception)}"

        else:
            return f"Error inesperado al {operation}: {str(exception)}"

    def _extract_api_error_message(self, response: requests.Response) -> str | None:
        """
        Extrae el mensaje de error específico de la respuesta de la API.

        Args:
            response: La respuesta HTTP de la API

        Returns:
            str | None: El mensaje de error de la API o None si no se puede extraer
        """
        try:
            # Intentar obtener JSON de la respuesta
            data = response.json()

            # Intentar diferentes campos comunes para mensajes de error
            possible_fields = [
                'message',    # Campo más común
                'error',      # Otro campo común
                'mensaje',    # En español
                'detail',     # Para APIs REST
                'description',# Descripción del error
                'msg'         # Abreviado
            ]

            for field in possible_fields:
                if field in data and data[field]:
                    return str(data[field])

            # Si no encuentra campos específicos, intentar buscar en objetos anidados
            if 'error' in data and isinstance(data['error'], dict):
                for field in possible_fields:
                    if field in data['error'] and data['error'][field]:
                        return str(data['error'][field])

            # Como último recurso, si hay contenido JSON pero sin campos conocidos
            # devolver una representación resumida
            if data:
                return f"Error de API: {str(data)[:100]}..."

            return None

        except (ValueError, TypeError, AttributeError):
            # Si no es JSON válido, intentar obtener texto plano
            try:
                text_content = response.text.strip()
                if text_content and len(text_content) < 200:
                    return text_content
                elif text_content:
                    return f"{text_content[:100]}..."
                return None
            except:
                return None
    
    def _get_address_data(self, codigo_postal: str) -> dict:
        """
        Obtiene datos de dirección (estado, municipio, colonia) basado en código postal.

        Args:
            codigo_postal (str): Código postal para consultar los datos de dirección

        Returns:
            dict: Datos de dirección con idEstado, idMunicipio, idColonia o error
        """
        try:
            # Validar código postal
            if not codigo_postal:
                return {
                    "success": False,
                    "error": "Código postal es requerido"
                }

            # Validar formato de código postal (5 dígitos)
            if not isinstance(codigo_postal, str) or not codigo_postal.isdigit() or len(codigo_postal) != 5:
                return {
                    "success": False,
                    "error": "Código postal debe ser una cadena de 5 dígitos"
                }

            # Validar configuración requerida
            required_configs = [
                ('URL_DATA_MAXI', settings.URL_DATA_MAXI),
                ('USRNAME_DATA_MAXI', settings.USRNAME_DATA_MAXI),
                ('PASSWORD_DATA_MAXI', settings.PASSWORD_DATA_MAXI)
            ]

            for config_name, config_value in required_configs:
                if not config_value:
                    return {
                        "success": False,
                        "error": f"Configuración faltante: {config_name}"
                    }

            # Configurar la URL y credenciales
            url = f"{settings.URL_DATA_MAXI}/sepomex/obtenerdireccion/completa"

            # Preparar los datos para el POST
            data: Dict[str, str] = {
                "id": codigo_postal
            }

            # Configurar headers
            headers: Dict[str, str] = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }

            # Realizar la petición POST con autenticación básica
            response: requests.Response = requests.post(
                url=url,
                json=data,
                headers=headers,
                auth=HTTPBasicAuth(settings.USRNAME_DATA_MAXI, settings.PASSWORD_DATA_MAXI),
                timeout=30
            )

            # Verificar el status code
            response.raise_for_status()

            # Procesar respuesta JSON
            response_data = response.json()

            # Validar estructura de la respuesta
            if not isinstance(response_data, dict):
                return {
                    "success": False,
                    "error": "Formato de respuesta inválido del servicio"
                }

            if "data" not in response_data:
                return {
                    "success": False,
                    "error": "No se encontraron datos para el código postal proporcionado"
                }

            data_list = response_data["data"]
            if not isinstance(data_list, list) or len(data_list) == 0:
                return {
                    "success": False,
                    "error": "No se encontraron datos de dirección para el código postal"
                }

            address_data = data_list[0]

            # Validar campos requeridos en la respuesta
            required_fields = ["idEstado", "idMunicipio", "idColonia"]
            missing_fields = [field for field in required_fields if field not in address_data or not address_data[field]]

            if missing_fields:
                return {
                    "success": False,
                    "error": f"Datos incompletos en la respuesta: faltan {', '.join(missing_fields)}"
                }

            # Retornar datos exitosos (IDs y nombres)
            return {
                "success": True,
                "idEstado": address_data.get("idEstado"),
                "idMunicipio": address_data.get("idMunicipio"),
                "idColonia": address_data.get("idColonia"),
                "estado": address_data.get("descripcionEstado", ""),
                "municipio": address_data.get("municipio", ""),
                "colonia": address_data.get("colonia", ""),
                "codigo_postal": codigo_postal
            }

        except requests.RequestException as e:
            error_msg = self._handle_request_exception(e, "obtener datos de dirección")
            return {
                "success": False,
                "error": error_msg
            }
        except (ValueError, KeyError, TypeError) as e:
            return {
                "success": False,
                "error": f"Error procesando respuesta del servicio: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error inesperado obteniendo datos de dirección: {str(e)}"
            }
    
    def _get_nearest_branch(self, codigo_postal: str, marca_moto: str) -> dict:
        """
        Obtiene la sucursal más cercana de una marca de motocicletas basada en el código postal.

        Utiliza Google Maps Platform APIs (New) con enfoque de 2 pasos:
        1. Geocoding API: Convierte código postal a coordenadas (lat/lon)
        2. Places API (New) - Text Search: Busca distribuidores/sucursales cercanas de la marca

        Args:
            codigo_postal (str): Código postal mexicano (5 dígitos)
            marca_moto (str): Marca de la motocicleta (ej: "Honda", "Bajaj", "Suzuki")

        Returns:
            dict: Datos de la sucursal más cercana con estructura:
                {
                    "status": "success" | "error",
                    "branch": {
                        "name": str,
                        "address": str,
                        "phone": str | None,
                        "website": str | None,
                        "distance": float,  # en kilómetros
                        "place_id": str
                    } | None,
                    "message": str (solo en caso de error)
                }
        """
        logger.info(f"🏢 Iniciando búsqueda de sucursal - Marca: '{marca_moto}', CP: '{codigo_postal}'")

        # Validar API key
        if not settings.GOOGLE_MAPS_API_KEY:
            logger.error("❌ GOOGLE_MAPS_API_KEY no configurada en settings")
            result = {
                "status": "error",
                "branch": None,
                "message": "API key de Google Maps no configurada"
            }
            logger.debug(f"Retornando error: {result}")
            return result

        # Validar parámetros
        if not codigo_postal or not marca_moto:
            logger.warning(f"⚠️ Parámetros incompletos - CP: '{codigo_postal}', Marca: '{marca_moto}'")
            result = {
                "status": "error",
                "branch": None,
                "message": "Código postal y marca son requeridos"
            }
            logger.debug(f"Retornando error: {result}")
            return result

        try:
            # PASO 1: Geocoding - Convertir código postal a coordenadas
            logger.info(f"📍 Paso 1/2: Geocodificando CP '{codigo_postal}' (México)")

            geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"
            geocode_params = {
                "address": codigo_postal,
                "components": "country:MX",
                "key": settings.GOOGLE_MAPS_API_KEY
            }

            logger.debug(f"Llamando Geocoding API: {geocode_url}")
            geocode_response = requests.get(geocode_url, params=geocode_params, timeout=10)
            geocode_response.raise_for_status()
            geocode_data = geocode_response.json()

            logger.debug(f"Geocoding API status: {geocode_data.get('status')}")

            if geocode_data.get('status') != 'OK' or not geocode_data.get('results'):
                logger.warning(f"⚠️ No se encontraron coordenadas para CP: {codigo_postal}")
                result = {
                    "status": "error",
                    "branch": None,
                    "message": f"No se pudo geocodificar el código postal: {codigo_postal}"
                }
                logger.debug(f"Retornando error: {result}")
                return result

            # Extraer coordenadas
            location = geocode_data['results'][0]['geometry']['location']
            lat = location['lat']
            lng = location['lng']
            logger.info(f"✅ Coordenadas obtenidas - Lat: {lat}, Lng: {lng}")
            logger.debug(f"Dirección formateada: {geocode_data['results'][0].get('formatted_address', 'N/A')}")

            # PASO 2: Places API (New) - Text Search
            logger.info(f"🔍 Paso 2/2: Buscando sucursales de '{marca_moto}' usando Places API (New)")

            # Construir queries de búsqueda optimizadas
            search_queries = [
                f"{marca_moto} motocicletas distribuidor México",
                f"{marca_moto} motos agencia México",
                f"{marca_moto} dealership Mexico"
            ]

            all_places = []

            # Usar Places API (New) - Text Search
            # Documentación: https://developers.google.com/maps/documentation/places/web-service/text-search
            places_url = "https://places.googleapis.com/v1/places:searchText"

            headers = {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": settings.GOOGLE_MAPS_API_KEY,
                "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.location,places,places.nationalPhoneNumber,places.websiteUri"
            }

            for idx, query in enumerate(search_queries):
                logger.debug(f"Búsqueda {idx + 1}/{len(search_queries)} - Query: '{query}'")

                try:
                    # Body para Text Search
                    request_body = {
                        "textQuery": query,
                        "locationBias": {
                            "circle": {
                                "center": {
                                    "latitude": lat,
                                    "longitude": lng
                                },
                                "radius": 50000.0  # 50 km en metros
                            }
                        },
                        "languageCode": "es",
                        "maxResultCount": 5
                    }

                    logger.debug(f"Llamando Places API (New): {places_url}")
                    places_response = requests.post(
                        places_url,
                        json=request_body,
                        headers=headers,
                        timeout=15
                    )
                    places_response.raise_for_status()
                    places_data = places_response.json()

                    results = places_data.get('places', [])
                    logger.debug(f"  → Encontrados {len(results)} resultado(s)")

                    # Agregar a la lista global (evitar duplicados por place_id)
                    existing_ids = {p.get('id') for p in all_places}
                    new_places = [p for p in results if p.get('id') not in existing_ids]
                    all_places.extend(new_places)

                    logger.debug(f"  → {len(new_places)} nuevo(s), total acumulado: {len(all_places)}")

                    # Si ya encontramos resultados en la primera búsqueda, podemos detenernos
                    if len(all_places) >= 3:
                        logger.debug("✅ Suficientes resultados encontrados, deteniendo búsqueda")
                        break

                except requests.RequestException as search_error:
                    logger.warning(f"⚠️ Error en búsqueda '{query}': {search_error}")
                    continue
                except Exception as search_error:
                    logger.warning(f"⚠️ Error inesperado en búsqueda '{query}': {search_error}")
                    continue

            if not all_places:
                logger.warning(f"⚠️ No se encontraron sucursales de '{marca_moto}' cerca del CP {codigo_postal}")
                result = {
                    "status": "success",
                    "branch": None,
                    "message": f"No se encontraron sucursales de {marca_moto} en un radio de 50km"
                }
                logger.debug(f"Retornando sin resultados: {result}")
                return result

            logger.info(f"✅ Total de sucursales encontradas: {len(all_places)}")

            # Tomar la primera (Places API ya ordena por relevancia/distancia)
            nearest_place = all_places[0]

            logger.debug(f"Sucursal más cercana/prominente: {nearest_place.get('displayName', {}).get('text', 'N/A')}")

            # Calcular distancia usando Haversine
            from math import radians, sin, cos, sqrt, atan2

            place_location = nearest_place.get('location', {})
            place_lat = place_location.get('latitude', lat)
            place_lng = place_location.get('longitude', lng)

            # Fórmula de Haversine para distancia entre dos puntos
            R = 6371  # Radio de la Tierra en km

            lat1, lon1 = radians(lat), radians(lng)
            lat2, lon2 = radians(place_lat), radians(place_lng)

            dlat = lat2 - lat1
            dlon = lon2 - lon1

            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            distance_km = R * c

            logger.debug(f"Distancia calculada: {distance_km:.2f} km")

            # Construir respuesta estructurada (Places API New tiene estructura diferente)
            branch_data = {
                "name": nearest_place.get('displayName', {}).get('text', 'N/A'),
                "address": nearest_place.get('formattedAddress', 'N/A'),
                "phone": nearest_place.get('nationalPhoneNumber'),
                "website": nearest_place.get('websiteUri'),
                "distance": round(distance_km, 2),
                "place_id": nearest_place.get('id', 'N/A')
            }

            result = {
                "status": "success",
                "branch": branch_data
            }

            logger.info(f"🎉 Sucursal encontrada exitosamente: {branch_data['name']}")
            logger.info(f"   └─ Dirección: {branch_data['address']}")
            logger.info(f"   └─ Distancia: {branch_data['distance']} km")
            logger.info(f"   └─ Teléfono: {branch_data['phone'] or 'No disponible'}")
            logger.debug(f"Retornando resultado: {result}")

            return result

        except requests.RequestException as req_error:
            error_msg = f"Error de request a Google Maps API: {str(req_error)}"
            logger.error(error_msg, exc_info=True)
            result = {
                "status": "error",
                "branch": None,
                "message": error_msg
            }
            logger.debug(f"Retornando error: {result}")
            return result

        except Exception as e:
            error_msg = f"Error inesperado buscando sucursal: {str(e)}"
            logger.error(error_msg, exc_info=True)
            result = {
                "status": "error",
                "branch": None,
                "message": error_msg
            }
            logger.debug(f"Retornando error: {result}")
            return result