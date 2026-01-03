from playwright.sync_api import sync_playwright, TimeoutError
import time
import random

def search_ofac(entity_name: str):
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True, 
            slow_mo=50  # Para tener delay y no quedar bloqueado
        )
        page = browser.new_page()
        page.goto("https://sanctionssearch.ofac.treas.gov/", wait_until="networkidle", timeout=60000)
        
        time.sleep(random.uniform(2, 4))

        # Esperar input principal
        page.wait_for_selector("#ctl00_MainContent_txtLastName", state="visible", timeout=10000)
        time.sleep(random.uniform(1, 2))
        page.fill("#ctl00_MainContent_txtLastName", entity_name)
        time.sleep(random.uniform(1, 2))
        # Click en Search
        page.click("#ctl00_MainContent_btnSearch")
        time.sleep(random.uniform(3, 5))

        try:
            page.wait_for_selector("#gvSearchResults", state="visible", timeout=20000)
            time.sleep(random.uniform(2, 3))
            # Buscar filas específicamente en la tabla gvSearchResults
            rows = page.query_selector_all("#gvSearchResults tr")

            for i, row in enumerate(rows, 1):
                cols = row.query_selector_all("td")
                #Name, Address, Type, Program, List, Score
                if len(cols) >= 6:
                    name_cell = cols[0]
                    name_link = name_cell.query_selector("a")
                    name_text = name_link.inner_text().strip() if name_link else name_cell.inner_text().strip()
                    name_url = name_link.get_attribute("href") if name_link else None
                    
                    result = {
                        "name": name_text,
                        "name_url": f"https://sanctionssearch.ofac.treas.gov/{name_url}" if name_url else None,
                        "address": cols[1].inner_text().strip(),
                        "type": cols[2].inner_text().strip(),
                        "programs": cols[3].inner_text().strip(),
                        "list": cols[4].inner_text().strip(),
                        "score": cols[5].inner_text().strip()
                    }
                    results.append(result)
                    print(f"  {i}. {result['name']} | {result['address']} | {result['type']} | {result['programs']} | Score: {result['score']}")

        except TimeoutError:
            print("No se encontraron resultados o timeout alcanzado")
            results = []
        time.sleep(3)
        
        browser.close()

    return {
        "source": "OFAC",
        "query": entity_name,
        "hits": len(results),
        "results": results
    }

# Ya no se usa en este archivo, pero útil para pruebas rápidas
if __name__ == "__main__":
    entity_name = input("Ingrese el nombre de la entidad a buscar en OFAC: ")
    data = search_ofac(entity_name)
    print(data)
