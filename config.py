"""
Configuración del scraper
"""

# URL BASE del World Bank Debarred Firms
BASE_URL = "https://projects.worldbank.org/en/projects-operations/procurement/debarred-firms"

"""
Cabeceras HTTP para la solicitud a World Bank
debido que al usar Postman , la página bloquea el request
"""
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

# Constantes de Reintentos en los scrapers, y delays para evitar bloqueos
MAX_RETRIES = 3
RETRY_DELAY = 2  # segundos

# Timeout de las solicitudes HTTP
REQUEST_TIMEOUT = 30  # segundos

# Directorio de salida para archivos
OUTPUT_DIR = "output"
# Extensión de los archivos de salida
OUTPUT_FORMATS = ['csv', 'json']