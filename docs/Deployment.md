# Cómo Instalar y Ejecutar

## Requisitos

- Python 3.9+
- pip
- Git

## Instalación

1. Clonar repo:S
```bash
git clone https://github.com/StylezZz/Ey-Prueba-Ejercicio-1.git
cd Ey-Prueba-Ejercicio-1
```

2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

3. Instalar Chromium para scraping:
```bash
playwright install chromium
```

## Ejecutar

```bash
python run.py
```

El servidor arranca en `http://localhost:8000`

## Verificar que funciona

```bash
curl http://localhost:8000/health
```

Si responde con `"status": "healthy"` está corriendo bien.

## Probar con Postman

1. Abrir Postman
2. Import → File
3. Seleccionar `Ey - Ejercicio 1.postman_collection.json`
4. Usar API Key: `demo-api-key-12345`

## Variables de entorno (opcional)

Si quieres cambiar configuración, edita `.env`:

```env
API_KEY_1=demo-api-key-12345
WORLD_BANK_API_KEY=z9duUaFUiEUYSHs97CU38fcZO7ipOPvm
RATE_LIMIT_PER_MINUTE=20
```
Por temas de facilidad paso el .env para pruebas sencillas, mi .gitignore si prevee la subida misma del .env

## Problemas comunes

**Error: "Playwright not found"**
```bash
playwright install chromium
```

**Error: "Rate limit exceeded"**  
Espera 1 minuto o usa otra API key.

**Offshore Leaks retorna "Challenge detected"**  
Es normal. El sitio detectó el bot. Intenta de nuevo en unos minutos.
 