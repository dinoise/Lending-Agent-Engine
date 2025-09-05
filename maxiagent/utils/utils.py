import requests
from bs4 import BeautifulSoup

def get_page_content(url) -> str:
    try:
        response: requests.Response = requests.get(url, timeout=10)
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