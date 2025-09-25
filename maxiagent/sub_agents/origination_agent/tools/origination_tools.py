import re
import uuid
import asyncio
import requests

from typing import List, Callable, Dict
from datetime import datetime

from google.adk.tools.tool_context import ToolContext
from ....config import current_config

class OriginationTools:
    """Clase para gestionar las herramientas del agente de originación."""

    def __init__(self):
        self._tools = {
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
            ine_front: str | None = tool_context.state.get('ine_front_image')
            ine_back: str | None = tool_context.state.get('ine_back_image')

            if not ine_front or not ine_back:
                return {
                    "status": "error",
                    "message": "Se requieren ambas imágenes del INE (frente y reverso)"
                }

            api_url: str = f"{current_config.URL_ORIGINADOR}/originacion/subir-ine"
            params: Dict[str, str] = {"uuidFlujo": flow_uuid}
            
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
            return {
                "status": "error",
                "message": f"Error durante la verificación: {str(e)}"
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
            valid: bool = validation.get('valid', False)
            if not valid:
                 return {
                    "status": "error",
                    "message": "El formato de la CURP no es válido."
                }

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

            blacklist_response, offers_response, renapo_response = await asyncio.gather(
                self._call_originador_api(blacklist_url, params),
                self._call_originador_api(offers_url, params),
                self._call_originador_api(renapo_url, params),
                return_exceptions=True
            )

            # Procesar respuestas
            results: Dict[str, str | bool] = {
                "status": "success",
                "curp": curp,
                "blacklist_check": "error",
                "active_offers_check": "error",
                "active_renapo_check": "error",
                "can_proceed": False
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

    # Ejecutar varias validaciones en paralelo usando asyncio
    async def _call_originador_api(self, url: str, params: dict) -> requests.Response:
        headers = {
            'User-Agent': 'Python-HTTP-Post-Client/1.0',
            'X-API-KEY': current_config.KEY_ORIGINADOR,
        }
        loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: requests.post(url, params=params, headers=headers, timeout=30)
        )

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