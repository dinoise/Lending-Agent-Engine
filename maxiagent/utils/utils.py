import requests

from os import getenv
from bs4 import BeautifulSoup
from google.cloud import secretmanager

# Initialize the Secrets client
SECRET_CLIENT = secretmanager.SecretManagerServiceClient()
"""
Google Cloud Secret Manager client.

Description:
------------
This client is used to access Google Cloud Secret Manager, allowing retrieval of secrets 
such as passwords, tokens, and other credentials that need to be securely stored.
"""

def get_page_content(url) -> str:
    try:
        # Usar session para un mejor manejo de conexiones
        with requests.Session() as session:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response: requests.Response = session.get(url, timeout=15, headers=headers)
            response.close()  # Cerrar explícitamente la respuesta

            soup = BeautifulSoup(response.text, 'html.parser')

            # Remover elementos no deseados
            for element in soup(['script', 'style', 'nav', 'footer', 'header', 'iframe', 'noscript']):
                element.decompose()

            # Estrategia 1: Buscar secciones específicas de productos/modelos
            relevant_content = []

            # Selectores comunes para secciones de productos/modelos de motos
            product_selectors = [
                # Selectores generales de productos
                '[class*="product"]', '[class*="modelo"]', '[class*="model"]',
                '[class*="bike"]', '[class*="moto"]', '[class*="vehicle"]',
                '[id*="product"]', '[id*="modelo"]', '[id*="model"]',
                # Selectores de catálogo
                '[class*="catalog"]', '[class*="catalogo"]', '[class*="grid"]',
                '[class*="card"]', '[class*="item"]',
                # Selectores de especificaciones y precios
                '[class*="spec"]', '[class*="price"]', '[class*="precio"]',
                # Elementos semánticos
                'article', 'section[class*="main"]', 'main'
            ]

            for selector in product_selectors:
                elements = soup.select(selector)
                for element in elements:
                    text = element.get_text(' ', strip=True)
                    # Filtrar elementos con contenido relevante (que mencionen precios o modelos)
                    if text and (
                        '$' in text or
                        'precio' in text.lower() or
                        'mxn' in text.lower() or
                        'cc' in text.lower() or  # cilindrada
                        'hp' in text.lower() or  # caballos de fuerza
                        'km/h' in text.lower()
                    ):
                        relevant_content.append(text)

            # Si encontramos contenido relevante, usarlo
            if relevant_content:
                combined_text = ' | '.join(relevant_content[:10])  # Top 10 secciones relevantes
                return combined_text[:2000]  # Aumentado a 2000 para tener más contexto

            # Estrategia 2: Buscar el contenido principal (main, article)
            main_content = soup.find(['main', 'article', 'div[role="main"], section, p'])
            if main_content:
                main_text = main_content.get_text(' ', strip=True)
                return main_text[:2000]

            # Estrategia 3: Fallback - extraer todo el texto pero con más caracteres
            all_text: str = soup.get_text(' ', strip=True)
            return all_text[:1500]

    except Exception as e:
        print(f"Error fetching page content from {url}: {e}")
        return ""
    
def get_secret(secret_name: str) -> str:
    """
    Retrieves the value of a secret stored in Google Cloud Secret Manager.

    Args:
        secret_name (str):Name of the secret in Google Cloud Secret Manager.

    Returns:
        str: Value of the requested secret.
    """

    project_id: str | None = getenv("GOOGLE_CLOUD_PROJECT")
    name: str = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
    try:
        response: secretmanager.AccessSecretVersionResponse = SECRET_CLIENT.access_secret_version(name=name)
    except Exception as e:
        print(f"Error retrieving the secret from GCP: {e}")
        raise Exception(e)
    return response.payload.data.decode('UTF-8')