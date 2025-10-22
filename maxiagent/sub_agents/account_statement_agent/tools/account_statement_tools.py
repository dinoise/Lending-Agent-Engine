import requests
from typing import List, Optional
from requests.auth import HTTPBasicAuth

from ....core import settings, get_logger
from ....tools.base_tools import BaseAgentTools

logger = get_logger(__name__)


class AccountStatementTools(BaseAgentTools):
    """Clase para gestionar las herramientas del agente de estados de cuenta."""

    def __init__(self):
        super().__init__()
        self._tools = {
            'tools': {
                'get_account_statement': self.get_account_statement
            }
        }
        logger.debug("AccountStatementTools inicializado")

    def get_account_statement(
        self,
        curp: Optional[str] = None,
        id_creditos: Optional[List[int]] = None,
        tipo_informe: int = 2
    ) -> dict:
        """
        Obtiene el estado de cuenta de creditos.

        Args:
            curp: CURP del usuario
            id_creditos: Lista de IDs de creditos
            tipo_informe: Tipo de informe (default: 2)

        Returns:
            Dict con el resultado de la consulta
        """
        if not curp and not id_creditos:
            return {
                "status": "error",
                "message": "Debe proporcionar CURP o ID de credito"
            }

        body = {"tipo_informe": tipo_informe}

        if curp:
            body["curp"] = curp.upper()

        if id_creditos:
            body["id_creditos"] = id_creditos

        url = f"{settings.URL_CREDITOS_MAXI}/v4/creditos/estado-cuenta-resumen"
        username = settings.USRNAME_CREDITOS_MAXI
        password = settings.PASSWORD_CREDITOS_MAXI

        try:
            response = requests.post(
                url,
                json=body,
                auth=HTTPBasicAuth(username, password) if username else None,
                headers={"Content-Type": "application/json"},
                timeout=30
            )

            if response.status_code == 200:
                return {
                    "status": "success",
                    "data": response.json()
                }
            else:
                return {
                    "status": "error",
                    "message": f"Error {response.status_code}",
                    "detail": response.text
                }

        except Exception as e:
            logger.error(f"Error en get_account_statement: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }