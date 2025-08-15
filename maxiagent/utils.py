import requests
from bs4 import BeautifulSoup

def get_page_content(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        # Extraer el texto de los párrafos principales
        paragraphs = ' '.join([p.get_text() for p in soup.find_all('p')][:100])
        return paragraphs[:10000]  # Limitar a 1000 caracteres
    except:
        return ""