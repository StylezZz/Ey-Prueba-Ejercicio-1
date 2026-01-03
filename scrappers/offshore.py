from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup
import pandas as pd
import json
import logging
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import time
import random

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ICIJOffshoreLeaksScraper:   
    BASE_URL = "https://offshoreleaks.icij.org"
    SEARCH_URL = f"{BASE_URL}/search"
    
    MIN_DELAY = 4  # segundos mínimos entre páginas
    MAX_DELAY = 10  # segundos máximos entre páginas
    MAX_PAGES_PER_RUN = 5
    
    def __init__(self, headless: bool = False):       
        self.headless = headless
        self.all_entities = []
        self.human_challenge_detected = False
        
    def human_delay(self, min_seconds: float = None, max_seconds: float = None):
        min_s = min_seconds or self.MIN_DELAY
        max_s = max_seconds or self.MAX_DELAY
        delay = random.uniform(min_s, max_s)
        time.sleep(delay)
    
    def simulate_human_reading(self, page):
        try:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.3)")
            time.sleep(random.uniform(0.5, 1.5))
            
            page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.6)")
            time.sleep(random.uniform(0.5, 1.5))
            
            page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.9)")
            time.sleep(random.uniform(0.5, 1.0))
            
            page.evaluate("window.scrollTo(0, 0)")
            time.sleep(random.uniform(0.3, 0.8))
            
        except Exception as e:
            logger.warning(f"No se pudo simular scroll: {e}")
    
    def detect_human_verification_challenge(self, html: str) -> bool:
        challenge_patterns = [
            "verify you are human",
            "verif",
            "human verification",
            "cloudfront",
            "aws waf",
            "checking your browser",
            "please wait",
            "just a moment",
            "security check"
        ]
        
        html_lower = html.lower()
        
        for pattern in challenge_patterns:
            if pattern in html_lower:
                logger.error(f"CHALLENGE DETECTADO: '{pattern}' encontrado en HTML, :(")
                return True
        
        return False
    
    def accept_terms(self, page) -> bool:
        try:
            logger.info("Buscando modal de términos y condiciones...")
            
            # Esperar el checkbox y marcarlo
            checkbox = page.locator('input[type="checkbox"]#accept')
            if checkbox.is_visible(timeout=5000):
                time.sleep(random.uniform(1, 2)) 
                checkbox.click()
                logger.info("Checkbox pasado")
                
                time.sleep(random.uniform(0.5, 1.5)) 
                
                # Submit
                submit_btn = page.locator('button[type="submit"]').filter(has_text="Submit")
                submit_btn.click()
                logger.info("Términos click")
                time.sleep(random.uniform(2, 4))
                return True
        except Exception as e:
            logger.warning(f"No se encontró modal de términos: {e}")
            return False
    
    def extract_entities_from_html(self, html: str, query: str) -> List[Dict]:
        entities = []
        soup = BeautifulSoup(html, 'html.parser')
        
        table = soup.find('table', class_='search__results__table')
        
        if not table:
            logger.warning("No se encontró tabla de resultados")
            return entities
        
        # Extraer filas de la tabla
        tbody = table.find('tbody')
        if not tbody:
            logger.warning("No se encontró tbody en la tabla")
            return entities
            
        rows = tbody.find_all('tr')
        
        if not rows:
            logger.warning("No hay filas en la tabla")
            return entities
                
        for row in rows:
            try:
                cells = row.find_all('td')
                
                if len(cells) >= 4:
                    entity_cell = cells[0]
                    entity_link = entity_cell.find('a')
                    entity_name = entity_link.get_text(strip=True) if entity_link else 'N/A'
                    entity_url = entity_link.get('href') if entity_link else None
                    
                    jurisdiction = cells[1].get_text(strip=True) or 'N/A'
                    linked_to = cells[2].get_text(strip=True) or 'N/A'
                    
                    data_from_cell = cells[3]
                    data_from_link = data_from_cell.find('a')
                    data_from = data_from_link.get_text(strip=True) if data_from_link else 'N/A'
                    data_from_url = data_from_link.get('href') if data_from_link else None
                    
                    entity = {
                        'entity_name': entity_name,
                        'entity_url': f"{self.BASE_URL}{entity_url}" if entity_url else None,
                        'jurisdiction': jurisdiction,
                        'linked_to': linked_to,
                        'data_from': data_from,
                        'data_from_url': data_from_url,
                        'search_query': query,
                        'scraped_at': datetime.now().isoformat()
                    }
                    
                    entities.append(entity)
                    
            except Exception as e:
                logger.error(f"Error al procesar fila: {e}")
                continue
        
        return entities
    
    def get_next_page_url(self, html: str) -> Optional[str]:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Buscar el botón "More results"
        more_btn = soup.find('a', {'data-more-results': True})
        
        if more_btn and more_btn.get('href'):
            next_url = more_btn.get('href')
            # Construir URL completa
            full_url = f"{self.BASE_URL}{next_url}"
            logger.info(f"Siguiente página encontrada: {next_url}")
            return full_url
        
        return None
    
    def scrape_search_results(self, query: str, max_pages: int = None) -> Tuple[List[Dict], bool]:
        entities = []
        self.human_challenge_detected = False
        
        if max_pages is None:
            max_pages = self.MAX_PAGES_PER_RUN
        
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=self.headless,
                slow_mo=50  
            )
            
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
                locale='en-US',
                timezone_id='America/New_York'
            )
            
            page = context.new_page()
            
            try:
                current_url = f"{self.SEARCH_URL}?q={query}"
                page_count = 0
                
                while current_url and page_count < max_pages:
                    page_count += 1                    
                    try:
                        page.goto(current_url, wait_until="networkidle", timeout=30000)
                    except PlaywrightTimeout:
                        time.sleep(3)
                    
                    if page_count == 1:
                        self.accept_terms(page)
                        self.human_delay(3, 6)
                    
                    self.simulate_human_reading(page)

                    html = page.content()
                    
                    if self.detect_human_verification_challenge(html):
                        self.human_challenge_detected = True
                        break
                    
                    page_entities = self.extract_entities_from_html(html, query)
                    
                    if page_entities:
                        entities.extend(page_entities)
                    else:
                        debug_file = f"debug_page_{page_count}.html"
                        with open(debug_file, 'w', encoding='utf-8') as f:
                            f.write(html)
                        break
                    
                    next_url = self.get_next_page_url(html)
                    
                    if next_url and page_count < max_pages:
                        current_url = next_url
                        
                        self.human_delay()
                    else:
                        if not next_url:
                            logger.info("No hay más páginas para procesar")
                        else:
                            logger.info(f"Límite de {max_pages} páginas alcanzado")
                        break
                
                print(f"\n{'='*60}")
                if self.human_challenge_detected:
                    print("Encontramos un challenge humano. ")
                else:
                    print("SCRAPING COMPLETADO")
                print(f"{'='*60}")
                print(f"Challenge detectado: {'SÍ' if self.human_challenge_detected else 'NO'}")
                print(f"{'='*60}")
                
            except Exception as e:
                logger.error(f"Error durante el scraping: {e}")
                import traceback
                traceback.print_exc()
                
            finally:
                time.sleep(2)
                browser.close()
        
        self.all_entities = entities
        return entities, self.human_challenge_detected
    
    def display_results(self, entities: List[Dict] = None, max_display: int = 20):
        if entities is None:
            entities = self.all_entities
        
        if not entities:
            print("\nNo hay resultados para mostrar")
            return
        
        print(f"\n{'='*60}")
        print(f"RESULTADOS ENCONTRADOS: {len(entities)}")
        print(f"{'='*60}\n")
        
        display_count = min(len(entities), max_display)
        
        for i, entity in enumerate(entities[:display_count], 1):
            print(f"{i}. Entity: {entity['entity_name']}")
            print(f"   Jurisdiction: {entity['jurisdiction']}")
            print(f"   Linked to: {entity['linked_to']}")
            print(f"   Data from: {entity['data_from']}")
            if entity.get('entity_url'):
                print(f"   URL: {entity['entity_url']}")
            print()
    
    def get_as_dataframe(self, entities: List[Dict] = None) -> pd.DataFrame:
        if entities is None:
            entities = self.all_entities
        
        if not entities:
            return pd.DataFrame()
        
        df = pd.DataFrame(entities)
        
        print(f"\n{'='*60}")
        print(f"DATAFRAME - {len(df)} registros")
        print(f"{'='*60}")
        print(df[['entity_name', 'jurisdiction', 'linked_to', 'data_from']].head(20))
        
        return df
    
    def save_to_csv(self, entities: List[Dict] = None, filename: str = None) -> str:
        if entities is None:
            entities = self.all_entities
        
        if not entities:
            logger.warning("No hay datos para guardar")
            return None
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"icij_offshore_leaks_{timestamp}.csv"
        
        os.makedirs('output', exist_ok=True)
        filepath = os.path.join('output', filename)
        
        df = pd.DataFrame(entities)
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        
        logger.info(f"Datos guardados en CSV: {filepath}")
        print(f"Done CSV: {filepath}")
        
        return filepath
    
    def save_to_json(self, entities: List[Dict] = None, filename: str = None) -> str:
        if entities is None:
            entities = self.all_entities
        
        if not entities:
            logger.warning("No hay datos para guardar")
            return None
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"icij_offshore_leaks_{timestamp}.json"
        
        os.makedirs('output', exist_ok=True)
        filepath = os.path.join('output', filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'source': self.SEARCH_URL,
                'total_entities': len(entities),
                'challenge_detected': self.human_challenge_detected,
                'data': entities
            }, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Datos guardados en JSON: {filepath}")
        print(f"Done JSON: {filepath}")
        
        return filepath

# Esto ya no se usa en este archivo, pero útil para pruebas rápidas
def main():
    scraper = ICIJOffshoreLeaksScraper(headless=False)
    
    while True:
        print("\n" + "="*60)
        print("MENÚ DE OPCIONES")
        print("="*60)
        print("1. Buscar entidades (con límite de seguridad)")
        print("2. Ver resultados actuales")
        print("="*60)
        
        opcion = input("\nSelecciona una opción: ").strip()
        
        if opcion == "1":
            query = input("\nIngresa el término de búsqueda: ").strip()
            if query:
                max_pages_input = input(f"¿Cuántas páginas? (Enter = {scraper.MAX_PAGES_PER_RUN}): ").strip()
                max_pages = int(max_pages_input) if max_pages_input.isdigit() else None
                
                entities, challenge = scraper.scrape_search_results(query, max_pages=max_pages)
                
                if challenge:
                    print("\nSe detectó challenge. Guarda los datos y espera antes de continuar.")
                
                scraper.display_results(entities)
            else:
                print("Debes ingresar un término de búsqueda")
        
        elif opcion == "2":
            scraper.display_results()
        else:
            print("\n No es una opción válida.")


if __name__ == "__main__":
    main()