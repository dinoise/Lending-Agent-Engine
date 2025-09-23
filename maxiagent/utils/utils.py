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
            response: requests.Response = session.get(url, timeout=10)
            response.close()  # Cerrar explícitamente la respuesta

            soup = BeautifulSoup(response.text, 'html.parser')

            # Remover elementos no deseados (scripts, estilos, etc.)
            for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                element.decompose()

            # Extraer TODO el texto de la página, incluyendo elementos anidados
            all_text: str = soup.get_text(' ', strip=True)

            return all_text[:10000]
    except Exception as e:
        print(f"Error: {e}")
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