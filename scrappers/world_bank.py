import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
from datetime import datetime
import time
import os
from dotenv import load_dotenv
from typing import List, Dict, Optional
import logging
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WorldBankScraper:
    API_URL = os.getenv('WORLD_BANK_API_URL')
    API_KEY = os.getenv('WORLD_BANK_API_KEY')
    WEB_URL = os.getenv('WORLD_BANK_WEB_URL')
        
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'apikey': self.API_KEY,
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.all_firms = []  
        self.api_firms = []  
        self.web_firms = []  
        
    def fetch_api_data(self, params: Dict = None, retries: int = 3) -> Optional[Dict]:
        if params is None:
            params = {}
            
        for attempt in range(retries):
            try:               
                response = self.session.get(
                    self.API_URL,
                    params=params,
                    timeout=30
                )                
                response.raise_for_status()
                
                data = response.json()
                logger.info(f"Obtención correcta de datos")
                return data
                
            except requests.HTTPError as e:
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    return None
                    
            except requests.RequestException as e:
                logger.warning(f"Error al consultar API (intento {attempt + 1}): {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    logger.error(f"Fallo tras {retries} intentos")
                    return None
                    
            except json.JSONDecodeError as e:
                print(f"Respuesta: {response.text[:500]}")
                return None
    
    def parse_api_response(self, data: Dict) -> List[Dict]:
        firms = []
        
        try:           
            # Como sabemos como esta estructurada la respuesta hacemos lo siguiente
            if 'response' in data and 'ZPROCSUPP' in data['response']:
                firms = data['response']['ZPROCSUPP']
            elif 'data' in data:
                firms = data['data']
            elif 'results' in data:
                firms = data['results']
            elif isinstance(data, list):
                firms = data
            else:
                firms = [data]
            # Almacenar los resultados completos
            self.all_firms = firms
            
        except Exception as e:
            logger.error(f"Error al parsear respuesta de API: {e}")
            
        return firms
    
    def filter_by_name(self, name: str, firms: List[Dict] = None) -> List[Dict]:
        if firms is None:
            firms = self.all_firms
        
        if not firms:
            logger.warning("No hay empresas para filtrar")
            return []
        
        name_lower = name.lower().strip()
        
        filtered = []
        for firm in firms:
            # Tomaremos de base el campo SUPP_NAME para hacer las búsquedas, sin consideras Address ni otro campo
            supp_name = firm.get('SUPP_NAME', '')
            if supp_name and name_lower in supp_name.lower():
                filtered.append(firm)        
        return filtered
    
    def search_by_filters(self, 
                          name: str = None, 
                          country: str = None,
                          country_code: str = None,
                          status: str = None,
                          firms: List[Dict] = None) -> List[Dict]:
        if firms is None:
            firms = self.all_firms
        
        if not firms:
            logger.warning("No hay empresas para filtrar")
            return []
        
        filtered = firms.copy()
        
        # Filtrar por nombre
        if name:
            name_lower = name.lower().strip()
            filtered = [f for f in filtered if name_lower in f.get('SUPP_NAME', '').lower()]
        
        # Filtrar por país
        if country:
            country_lower = country.lower().strip()
            filtered = [f for f in filtered if country_lower in f.get('COUNTRY_NAME', '').lower()]
        
        # Filtrar por código de país
        if country_code:
            country_code_upper = country_code.upper().strip()
            filtered = [f for f in filtered if f.get('LAND1', '') == country_code_upper]
        
        # Filtrar por estado
        if status:
            status_upper = status.upper().strip()
            filtered = [f for f in filtered if status_upper in f.get('ELIG_STAT', '').upper()]
                
        return filtered
    
    def display_firm_list(self, firms: List[Dict]):
        if not firms:
            print("\n No se encontraron empresas para mostrar")
            return
        
        for i, firm in enumerate(firms, 1):
            print(f"\n{i}. Firm Name: {firm.get('SUPP_NAME', 'N/A')}")
            print(f"    Country: {firm.get('COUNTRY_NAME', 'N/A')}")
            print(f"    Address: {firm.get('SUPP_ADDR', 'N/A')}")
            print(f"    Ineligibility Period: {firm.get('DEBAR_FROM_DATE', 'N/A')} - {firm.get('DEBAR_TO_DATE', 'N/A')}")
            
    def display_firm_details(self, firm: Dict):
        print("\n" + "="*60)
        print(f"FIRM NAME: {firm.get('SUPP_NAME', 'N/A')}")
        print("="*60)
        print(f"Address: {firm.get('SUPP_ADDR', 'N/A')}")
        print(f"Country: {firm.get('COUNTRY_NAME', 'N/A')}")
        print(f"\nINELIGIBILITY PERIOD:")
        print(f"  FROM DATE: {firm.get('DEBAR_FROM_DATE', 'N/A')}")
        print(f"  TO DATE: {firm.get('DEBAR_TO_DATE', 'N/A')}")
        print(f"\nGROUNDS: {firm.get('DEBAR_REASON', 'N/A')}")
        print("="*60)
    
    def scrape(self, params: Dict = None) -> List[Dict]:        
        data = self.fetch_api_data(params)
        
        if not data:
            logger.error("No se pudo obtener datos de la API")
            return []
        firms = self.parse_api_response(data)
        
        if firms:           
            if len(firms) > 0:
                print("\n" + "="*60)
                print("Ejemplo de registro a tomar en consideración:")
                print("="*60)
                sample = firms[0]
                print(json.dumps(sample, indent=2, ensure_ascii=False)[:800])
                print("...")
                print(f"\n: {list(sample.keys()) if isinstance(sample, dict) else 'N/A'}")
        
        return firms

# Esto ya no se usa en este archivo, pero útil para pruebas rápidas
def main():
    print("=" * 60)
    print("World Bank Debarred Firms - API Client")
    print("=" * 60)
    print()
    
    client = WorldBankScraper()
    
    all_firms = client.scrape()
    
    if not all_firms:
        print("\n No se obtuvieron datos")
        return
    
    while True:
        print("\n" + "="*60)
        print("MENÚ DE OPCIONES")
        print("="*60)
        print("1. Ver todas las empresas")
        print("2. Buscar por nombre")
        print("="*60)
        
        opcion = input("\nSelecciona una opción: ").strip()
        
        if opcion == "1":
            # Ver todas
            df = client.get_as_dataframe(all_firms)
            print(f"\n✅ Total: {len(all_firms)} empresas")
            
        elif opcion == "2":
            # Buscar por nombre
            nombre = input("\nIngresa el nombre a buscar: ").strip()
            if nombre:
                resultados = client.filter_by_name(nombre)
                if resultados:
                    if len(resultados) > 2:
                        # Mostrar lista completa
                        client.display_firm_list(resultados)
                    else:
                        # Mostrar detalles completos de cada uno
                        for firm in resultados:
                            client.display_firm_details(firm)
                else:
                    print("\n No se encontraron resultados")
        else:
            print("\n No es una opción")


if __name__ == "__main__":
    main()