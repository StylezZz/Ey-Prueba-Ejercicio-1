# Ejercicio 1: Web Scraping para búsqueda en listas de alto riesgo

## Objetivo
Desarrollar un servicio automatizado que permita identificar si una entidad se encuentra relacionada con listas de alto riesgo, tales como sanciones internacionales y bases de datos públicas, simulando un escenario de debida diligencia dentro de una institución financiera.

---

## Enfoque de la solución
Se implementó un **REST API** que recibe el nombre de una entidad y ejecuta procesos de **web scraping** sobre diversas fuentes públicas de riesgo.  
El servicio consolida los resultados obtenidos y los presenta de forma estructurada, incluyendo el número de coincidencias encontradas y el detalle por fuente.

---

## Tecnología utilizada
- Lenguaje: **Python**
- Framework: **FastAPI**
- Formato de respuesta: **JSON**
- Pruebas: **Postman**

FastAPI fue elegido por su rapidez de desarrollo, rendimiento y soporte nativo para APIs REST modernas.

---

## Fuentes consultadas

### Offshore Leaks Database (ICIJ)
- URL: https://offshoreleaks.icij.org
- Atributos obtenidos:
  - Entity
  - Jurisdiction
  - Linked To
  - Data From

### OFAC Sanctions Search
- URL: https://sanctionssearch.ofac.treas.gov/
- Atributos obtenidos:
  - Name
  - Address
  - Type
  - Program(s)
  - List
  - Score

---

## Diseño del REST API

### Endpoint principal
**POST** `/api/v1/search/all`

#### Payload de entrada
```json
{
  "entity_name": "MAX"
}
```

La API valida la entrada, ejecuta las búsquedas en las fuentes configuradas y retorna los resultados consolidados.

---
### Respuesta de la API
```json
{
  "total_matches": 3,
  "results": [
    {
      "source": "Offshore Leaks Database",
      "matches": [
        {
          "entity": "MAXIMUS INC",
          "jurisdiction": "US",
          "linked_to": "John Doe",
          "data_from": "2020-01-15"
        }
      ]
    },
    {
      "source": "OFAC Sanctions Search",
      "matches": [
        {
          "name": "MAXWELL LTD",
          "address": "123 Main St, Anytown, USA",
          "type": "Individual",
          "programs": ["SDN"],
          "list": "Specially Designated Nationals",
          "score": 95
        },
        {
          "name": "MAX CORPORATION",
          "address": "456 Elm St, Othertown, USA",
          "type": "Entity",
          "programs": ["SSI"],
          "list": "Sectoral Sanctions Identifications",
          "score": 88
        }
      ]
    }
  ]
}
```

---
### Validaciones y manejo de errores
- Autenticación mediante API Key.
- Validación del payload de entrada.
- Manejo de errores ante:
    - Fallos en las fuentes externas.
    - Resultados vacios.
    - Errores de scraping

El sistema se encuentra preparado para incorporar límites de llamadas por minuto según la necesidad.

---
### Decisiones técnicas
- Se utilizo web scraping debido a la ausencia de algunas APIs en algunas fuentes.
- Se normalizo la estructrua de salida para facilitar la integración.
- Se implemento autenticación para proteger el uso del servicio.