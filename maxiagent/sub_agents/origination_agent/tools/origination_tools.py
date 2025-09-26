import re
import asyncio
import requests

from typing import List, Callable, Dict

from google.adk.tools.tool_context import ToolContext
from ....config import current_config

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
            'quotation_flow': {
                'initialize_flow': self.initialize_flow,
                'process_ine_documents': self.process_ine_documents,
                'verify_ine_processing': self.verify_ine_processing,
                'validate_curp': self.validate_curp,
                'submit_form_data': self.submit_form_data,
                'send_nip': self.send_nip,
                'confirm_nip': self.confirm_nip,
                'resend_nip': self.resend_nip,
                'query_offers': self.query_offers
            },
            'validation_tools': {
                'validate_required_data': self.validate_required_data,
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

    # === New Quotation Flow Methods ===

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
            ine_front: str | None = tool_context.state.get('ine_front_image')
            ine_back: str | None = tool_context.state.get('ine_back_image')

            if not ine_front or not ine_back:
                return {
                    "status": "error",
                    "message": "Se requieren ambas imágenes del INE (frente y reverso)"
                }

            api_url: str = f"{current_config.URL_ORIGINADOR}/originacion/subir-ine"
            params: Dict[str, str] = {"uuidFlujo": flow_uuid}

            payload = {
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
                    
                    print(f"response ine processing {data}. attempt {attempt}")
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

    async def validate_curp(self, tool_context: ToolContext) -> dict:
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

    async def submit_form_data(self, tool_context: ToolContext, additional_data: dict) -> dict:
        """
        Envía los datos del formulario completo al API.

        Args:
            additional_data: Datos adicionales del usuario (celular, email.)

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
                "ingresoMensual": None,
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
            required_fields: List[str] = ['celular', 'curp', 'correoElectronico', 'precioMoto', 'marcaMoto', 'modeloMoto']
            missing_fields: List[str] = [field for field in required_fields if not form_data.get(field)]

            if missing_fields:
                return {
                    "status": "error",
                    "message": f"Campos requeridos faltantes: {', '.join(missing_fields)}"
                }

            api_url = f"{current_config.URL_ORIGINADOR}/originacion/capturar-formulario"
            params: Dict[str, str] = {"uuidFlujo": flow_uuid}

            response: requests.Response = await self._call_originador_api(
                api_url,
                method='POST',
                params=params,
                json_data=form_data,
                timeout=30
            )
            print(f"FORM RES {response.json()}")

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

    async def send_nip(self, tool_context: ToolContext) -> dict:
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

            response = await self._call_originador_api(
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

    async def confirm_nip(self, tool_context: ToolContext, nip: str) -> dict:
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

            response: requests.Response = await self._call_originador_api(
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

            response = await self._call_originador_api(
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

    async def query_offers(self, tool_context: ToolContext) -> dict:
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

            print(f"offers_data {offers_data}")

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