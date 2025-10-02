from __future__ import annotations

import re
import asyncio
import logging
import requests

from requests.auth import HTTPBasicAuth
from typing import List, Callable, Dict

from google.adk.tools.tool_context import ToolContext
from ....config import current_config

logger = logging.getLogger(__name__)

class OriginationTools:
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
        self._tools = {
            'chained_tools': {
                'process_ine_complete': self.process_ine_complete,
                'complete_form_and_nip': self.complete_form_and_nip,
                'confirm_nip_and_get_offers': self.confirm_nip_and_get_offers
            },
            'quotation_flow': {
                'initialize_flow': self.initialize_flow,
                'resend_nip': self.resend_nip,
                'select_offer': self.select_offer
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
                return {
                    "status": "error",
                    "step": "process_ine_documents",
                    "message": f"Fallo en procesamiento INE: {process_result.get('message')}"
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
                "next_step": "Ahora necesito que me proporciones: celular, correo electrónico y precio de la moto."
            }

        except Exception as e:
            logger.error(f"Error en proceso completo de INE: {e}")
            return {
                "status": "error",
                "message": f"Error inesperado en proceso de INE: {str(e)}"
            }

    async def complete_form_and_nip(self, tool_context: ToolContext, additional_data: dict) -> dict:
        """
        TOOL ENCADENADA: Ejecuta automáticamente los pasos 5-6 (formulario + NIP).

        Pasos que ejecuta:
        1. submit_form_data() - Envía formulario con datos adicionales
        2. send_nip() - Solicita envío de NIP automáticamente

        Args:
            additional_data: Dict con {celular, correoElectronico, precioMoto}

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

            logger.info("✨ Formulario enviado y NIP solicitado exitosamente")

            return {
                "status": "success",
                "message": "✅ Formulario enviado exitosamente\n\n📱 He solicitado el envío de un NIP de 6 dígitos a tu celular.\n\n⏱️ Por favor, revisa tu teléfono y proporciónameEL NIP cuando lo recibas.",
                "next_step": "Esperando NIP del usuario"
            }

        except Exception as e:
            logger.error(f"Error en proceso de formulario + NIP: {e}")
            return {
                "status": "error",
                "message": f"Error inesperado: {str(e)}"
            }

    async def confirm_nip_and_get_offers(self, tool_context: ToolContext, nip: str) -> dict:
        """
        TOOL ENCADENADA: Ejecuta automáticamente los pasos 7-8 (confirmar NIP + consultar ofertas).

        Pasos que ejecuta:
        1. confirm_nip() - Confirma el NIP de 6 dígitos
        2. query_offers() - Consulta ofertas automáticamente

        Args:
            nip: NIP de 6 dígitos proporcionado por el usuario

        Returns:
            Dict con ofertas disponibles formateadas
        """
        logger.info("🔗 Iniciando confirmación NIP + consulta de ofertas (pasos 7-8)")

        try:
            # Paso 7: Confirmar NIP
            logger.info("🔐 Paso 7: Confirmando NIP...")
            nip_result = await self._confirm_nip(tool_context, nip)

            if nip_result.get('status') != 'success':
                return {
                    "status": "error",
                    "step": "confirm_nip",
                    "message": f"Fallo en confirmación de NIP: {nip_result.get('message')}"
                }

            # Paso 8: Consultar ofertas automáticamente
            logger.info("💰 Paso 8: Consultando ofertas...")
            offers_result = await self._query_offers(tool_context)

            if offers_result.get('status') != 'success':
                return {
                    "status": "error",
                    "step": "query_offers",
                    "message": f"Fallo en consulta de ofertas: {offers_result.get('message')}"
                }

            logger.info("✨ NIP confirmado y ofertas consultadas exitosamente")

            return {
                "status": "success",
                "message": "✅ NIP confirmado exitosamente",
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
        try:
            api_url = f"{current_config.URL_ORIGINADOR}/originacion/nuevo-flujo"

            response = await self._call_originador_api(api_url, method='GET')

            data = response.json()
            flow_uuid = data.get('uuidFlujo')

            if not flow_uuid:
                raise ValueError("No se recibió flow_uuid del servidor")

            # Guardar en estado de sesión
            tool_context.state['flow_uuid'] = flow_uuid

            return {
                "status": "success",
                "message": f"Flujo inicializado exitosamente."
            }

        except requests.RequestException as e:
            error_msg = self._handle_request_exception(e, "inicializar flujo")
            print(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
        except Exception as e:
            error_msg = f"Error inesperado inicializando flujo: {e}"
            print(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }

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

            if not ine_front or not ine_back:
                return {
                    "status": "error",
                    "message": "Se requieren ambas imágenes del INE (frente y reverso)"
                }

            api_url: str = f"{current_config.URL_ORIGINADOR}/originacion/subir-ine"
            params: Dict[str, str] = {"uuidFlujo": flow_uuid}

            payload: Dict[str, str] = {
                "frenteBase64": ine_front,
                "reversoBase64": ine_back
            }

            await self._call_originador_api(
                api_url,
                method='POST',
                params=params,
                json_data=payload,
                timeout=60
            )

            return {
                "status": "success",
                "message": "Documentos INE enviados para procesamiento"
            }

        except requests.RequestException as e:
            error_msg = self._handle_request_exception(e, "procesar documentos INE")
            print(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
        except Exception as e:
            error_msg = f"Error inesperado procesando documentos INE: {e}"
            print(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }

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
            
            api_url = f"{current_config.URL_ORIGINADOR}/originacion/estatus-ine"
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
            print(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }

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
            
            api_base: str | None = current_config.URL_ORIGINADOR
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
            additional_data: Datos adicionales del usuario (celular, email.)

        Returns:
            Dict con resultado del envío
        """
        try:
            user_data: dict = tool_context.state.get('user_data', {})
            if not user_data:
                return {
                    "status": "error",
                    "message": "Datos de usuario no disponibles. Procesa INE primero."
                }

            flow_uuid: str = tool_context.state.get('flow_uuid')
            if not flow_uuid:
                return {
                    "status": "error",
                    "message": "Flujo no inicializado"
                }
            
            codigoPostal = user_data.get('codigoPostal')
            if not codigoPostal:
                return {
                    "status": "error",
                    "message": "Código postal no disponible en los datos del INE"
                }

            # Obteniendo los datos de dirección
            address_data: dict = self._get_address_data(codigoPostal)

            # Validar que se obtuvieron los datos de dirección correctamente
            if not address_data.get('success', False):
                error_msg = address_data.get('error', 'Error desconocido obteniendo datos de dirección')
                return {
                    "status": "error",
                    "message": f"No se pudieron obtener los datos de dirección: {error_msg}"
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
                "codigoPostal": codigoPostal,
                "rfc": user_data.get('rfc'),
                "correoElectronico": additional_data.get('correoElectronico'),
                "ingresoMensual": None,
                "precioMoto": additional_data.get('precioMoto'),
                "enganche": None,
                "numeroPromotor": "MAXIAGENT",
                "marcaMoto": additional_data.get('marcaMoto'),
                "modeloMoto": additional_data.get('modeloMoto'),
                "estado": address_data.get("idEstado"),
                "municipio": address_data.get("idMunicipio"),
                "colonia": address_data.get("idColonia"),
                "fk_usuario_creacion": "",
                "mostrarCampos": None
            }

            # Validar datos requeridos
            required_fields: List[str] = ['celular', 'curp', 'correoElectronico', 'precioMoto']
            missing_fields: List[str] = [field for field in required_fields if not form_data.get(field)]

            # Validar datos de dirección requeridos
            address_required_fields: List[str] = ['estado', 'municipio', 'colonia']
            missing_address_fields: List[str] = [field for field in address_required_fields if not form_data.get(field)]

            all_missing_fields = missing_fields + missing_address_fields

            if all_missing_fields:
                return {
                    "status": "error",
                    "message": f"Campos requeridos faltantes: {', '.join(all_missing_fields)}"
                }

            api_url = f"{current_config.URL_ORIGINADOR}/originacion/capturar-formulario"
            params: Dict[str, str] = {"uuidFlujo": flow_uuid}

            requests.Response = await self._call_originador_api(
                api_url,
                method='POST',
                params=params,
                json_data=form_data,
                timeout=30
            )

            # Guardar datos del formulario en estado
            tool_context.state['form_data'] = form_data

            return {
                "status": "success",
                "message": "Formulario enviado exitosamente",
                "form_data": form_data
            }

        except requests.RequestException as e:
            error_msg = self._handle_request_exception(e, "enviar formulario")
            print(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
        except Exception as e:
            error_msg = f"Error inesperado enviando formulario: {e}"
            print(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }

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

            api_url = f"{current_config.URL_ORIGINADOR}/originacion/pedir-nip"
            params = {"uuidFlujo": flow_uuid}

            await self._call_originador_api(
                api_url,
                method='GET',
                params=params,
                timeout=30
            )

            # Guardar estado del NIP
            tool_context.state['nip_requested'] = True

            return {
                "status": "success",
                "message": "NIP enviado exitosamente. El usuario debe revisar su teléfono celular."
            }

        except requests.RequestException as e:
            error_msg = self._handle_request_exception(e, "enviar NIP")
            print(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
        except Exception as e:
            error_msg = f"Error inesperado enviando NIP: {e}"
            print(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }

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

            api_url = f"{current_config.URL_ORIGINADOR}/originacion/confirmar-nip"
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
            print(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
        except Exception as e:
            error_msg = f"Error inesperado confirmando NIP: {e}"
            print(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }

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

            api_url = f"{current_config.URL_ORIGINADOR}/originacion/reenviar-nip"
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
            print(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
        except Exception as e:
            error_msg = f"Error inesperado reenviando NIP: {e}"
            print(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }

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

            # Verificar que el NIP haya sido confirmado
            nip_confirmed = tool_context.state.get('nip_confirmed', False)
            if not nip_confirmed:
                return {
                    "status": "error",
                    "message": "NIP no confirmado. Confirma el NIP usando confirm_nip primero."
                }

            api_url = f"{current_config.URL_ORIGINADOR}/originacion/consultar-ofertas"
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
            print(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
        except Exception as e:
            error_msg = f"Error inesperado consultando ofertas: {e}"
            print(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }

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
                return {
                    "status": "error",
                    "message": f"Plazo '{plazo_selected}' no está disponible en las ofertas consultadas. Plazos disponibles: {', '.join(available_plazos)}"
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
            api_url = f"{current_config.URL_ORIGINADOR}/originacion/seleccionar-oferta"
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

            # Obtener datos del estado para enviar a n8n
            user_data = tool_context.state.get('user_data', {})
            form_data = tool_context.state.get('form_data', {})

            curp = user_data.get('curp', '')
            celular = form_data.get('celular', '')
            email = form_data.get('correoElectronico', '')

            # Preparar payload para n8n
            flow_payload = {
                **selected_offer_data,
                "curp": curp,
                "celular": celular,
                "email": email,
                "flow_uuid": flow_uuid,
                "plazo": plazo_selected
            }

            # Realizar POST a Workflows
            try:
                flow_url: str = f"{current_config.API_MAXIKASH}/api/trigger-workflow"
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

            return {
                "status": "success",
                "message": f"Oferta de {plazo_selected} semanas seleccionada exitosamente",
                "plazo": plazo_selected
            }

        except requests.RequestException as e:
            error_msg = self._handle_request_exception(e, "seleccionar oferta")
            print(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
        except Exception as e:
            error_msg = f"Error inesperado seleccionando oferta: {e}"
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
            'X-API-KEY': current_config.KEY_ORIGINADOR,
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

            print(f"status_code {status_code}. API message: {api_message}")

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
                ('URL_DATA_MAXI', current_config.URL_DATA_MAXI),
                ('USRNAME_DATA_MAXI', current_config.USRNAME_DATA_MAXI),
                ('PASSWORD_DATA_MAXI', current_config.PASSWORD_DATA_MAXI)
            ]

            for config_name, config_value in required_configs:
                if not config_value:
                    return {
                        "success": False,
                        "error": f"Configuración faltante: {config_name}"
                    }

            # Configurar la URL y credenciales
            url = f"{current_config.URL_DATA_MAXI}/sepomex/obtenerdireccion/completa"

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
                auth=HTTPBasicAuth(current_config.USRNAME_DATA_MAXI, current_config.PASSWORD_DATA_MAXI),
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

            # Retornar datos exitosos
            return {
                "success": True,
                "idEstado": address_data["idEstado"],
                "idMunicipio": address_data["idMunicipio"],
                "idColonia": address_data["idColonia"],
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