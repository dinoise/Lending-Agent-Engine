import os

from dotenv import load_dotenv
from googleapiclient.discovery import build
from vertexai.preview import rag

from google.cloud.aiplatform_v1beta1.types.vertex_rag_service import RetrieveContextsResponse

load_dotenv()

def rag_response(query: str) -> str:
    """Retorna información contextual relevante desde el Curpus RAG.

    Args:
        query (str): El término de búsqueda.

    Returns:
        str: La respuesta conteniendo la información obtenida del corpus.
    """
    corpus_name = os.getenv("RAG_CORPUS")

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
    service = build("customsearch", "v1", developerKey=os.environ.get("GOOGLE_SEARCH_API_KEY"))
    res = service.cse().list(
        q=query,
        cx=os.environ.get("GOOGLE_CSE_ID"),  # ID del motor de búsqueda personalizado
        num=5  # Número de resultados
    ).execute()
    
    return {
        "status": "success",
        "results": [{
            "title": item["title"],
            "link": item["link"],
            "snippet": item["snippet"]
        } for item in res.get("items", [])]
    }