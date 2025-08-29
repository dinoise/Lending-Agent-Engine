import requests
import json
from datetime import datetime

from . import current_config
from .utils import get_page_content

from googleapiclient.discovery import build
from vertexai.preview import rag

from google.cloud.aiplatform_v1beta1.types.vertex_rag_service import RetrieveContextsResponse

def rag_response(query: str) -> str:
    """Retorna información contextual relevante desde el Curpus RAG.

    Args:
        query (str): El término de búsqueda.

    Returns:
        str: La respuesta conteniendo la información obtenida del corpus.
    """
    corpus_name = current_config.RAG_CORPUS

    rag_retrieval_config = rag.RagRetrievalConfig(
        top_k=3,
        filter=rag.Filter(vector_distance_threshold=0.5),
    )
    response: RetrieveContextsResponse = rag.retrieval_query(
        rag_resources=[
            rag.RagResource(
                rag_corpus=corpus_name,
            )
        ],
        text=query,
        rag_retrieval_config=rag_retrieval_config,
    )
    return str(response)

def google_web_search(query: str) -> dict:
    """Realiza una búsqueda en la web usando Google Custom Search JSON API.
    
    Args:
        query (str): Término de búsqueda
        
    Returns:
        dict: Resultados de la búsqueda con título, enlace y snippet
    """
    service = build("customsearch", "v1", developerKey=current_config.GOOGLE_SEARCH_API_KEY)
    res = service.cse().list(
        q=query,
        cx=current_config.GOOGLE_CSE_ID,
        num=5
    ).execute()
    
    results = []
    for item in res.get("items", []):
        # Obtener contenido extendido de la página
        extended_content = get_page_content(item["link"])
        
        results.append({
            "title": item["title"],
            "link": item["link"],
            "snippet": item["snippet"],
            "extended_content": extended_content
        })
    
    return {"status": "success", "results": results}

def calculate_offers(
        ingreso_mensual: float,
        precio_moto: float,
        fecha_nacimiento: str,
        marca_moto: str,
        modelo_moto: str
) -> list:
    """Calcula ofertas de financiamiento para motocicletas basado en ingresos y características del vehículo.
    
    Args:
        ingreso_mensual: Ingreso mensual del cliente en pesos mexicanos
        precio_moto: Precio de la motocicleta en pesos mexicanos
        fecha_nacimiento: Fecha de nacimiento del cliente en formato DD/MM/YY
        marca_moto: Marca de la motocicleta (ej. Honda, Yamaha, etc.)
        modelo_moto: Modelo específico de la motocicleta
        
    Returns:
        Dict con las opciones de financiamiento calculadas
    """
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Python-HTTP-Post-Cli ent/1.0',
        'Authorization': current_config.KEY_CALCULADORA,
        'usuario': ''
    }

    data: dict = {
        "ingresoMensual": ingreso_mensual,
        "precioMoto": precio_moto,
        "garantia": None,
        "fechaNacimiento": fecha_nacimiento,
        "idMunicipio": 1,
        "idEstado": 1,
        "codigoPostal": "06850",
        "idSucursal": 1,
        "idDistribuidor": 1,
        "marcaMoto": marca_moto,
        "modeloMoto": modelo_moto,
        "fechaHoraCreacionOferta": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "idUsuarioCreacion": "111",
        "idOferta": "111",
        "idPais": "MX"
    }
    

    try:
        response: requests.Response = requests.post(
            url=current_config.URL_CALCULADORA,
            json=data,
            headers=headers,
            timeout=30
        )
        print("RESPOSNEEE ", response)
        response.raise_for_status()
        
        try:
            return response.json()["output"]["calculos"]
        except json.JSONDecodeError:
            print( response.text )
            return []
        except Exception:
            print( response.text )
            return []
            
    except requests.exceptions.RequestException as e:
        print( f"ERROR {e}" )
        return []
     