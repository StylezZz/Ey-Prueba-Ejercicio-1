# API de Búsqueda en Listas de Riesgo

API REST para buscar entidades en listas de sanciones y alto riesgo financiero.

## Qué hace

Busca un nombre en 3 fuentes:
- OFAC 
- Offshore Leaks 
- World Bank 

## Instalación

```bash
git clone https://github.com/StylezZz/Ey-Prueba-Ejercicio-1.git
cd Ey-Prueba-Ejercicio-1
pip install -r requirements.txt
playwright install chromium
python run.py
```

El backend estará levantado en: `http://localhost:8000`

## Uso

Todas las requests necesitan header: `X-API-KEY: demo-api-key-12345` (Prueba, no se encuentra el .env)

### Buscar en OFAC
```bash
curl -X POST http://localhost:8000/api/v1/search/ofac \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: demo-api-key-12345" \
  -d '{"entity_name": "PEMEX"}'
```

### Buscar en todas las fuentes
```bash
curl -X POST http://localhost:8000/api/v1/search/all \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: demo-api-key-12345" \
  -d '{"entity_name": "Bank"}'
```

## Endpoints

- `GET /health` - Verificar si está corriendo
- `POST /api/v1/search/ofac` - Solo OFAC
- `POST /api/v1/search/offshore-leaks` - Solo Offshore
- `POST /api/v1/search/world-bank` - Solo World Bank
- `POST /api/v1/search/all` - Todas las fuentes
- `GET /api/v1/rate-limit` - Ver límite de requests

## Estructura

```
.
├── api/
│   ├── main.py          # Endpoints
│   ├── auth.py          # API Keys
│   ├── models.py        # Modelos de datos
│   └── rate_limiter.py  # Control de límite
├── scrappers/
│   ├── ofac.py          # Scraper OFAC
│   ├── offshore.py      # Scraper Offshore Leaks
│   └── world_bank.py    # Cliente World Bank API
├── run.py               # Iniciar servidor
└── requirements.txt
```

## Limitaciones

- Rate limit: 20 requests/minuto
- Offshore Leaks a veces detecta bot (retorna error)
- Los scrapers dependen de la estructura HTML actual

## Tecnologías

- FastAPI
- Playwright
- BeautifulSoup4
- Uvicorn

## Postman

Importa `Ey - Ejercicio 1.postman_collection.json` para probar todos los endpoints.

## Documentación

Ver `docs/` y revisar el documento "Documentación Ejercicio 1 - Final.pdf"
