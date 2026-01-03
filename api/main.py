from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import asyncio
from typing import Dict, List
import logging

from api.models import (
    EntitySearchRequest,
    SearchResponse,
    MultiSourceSearchResponse,
    ErrorResponse,
    HealthCheckResponse
)

from api.auth import get_api_key
from api.rate_limiter import check_rate_limit, rate_limiter

from scrappers.ofac import search_ofac
from scrappers.offshore import ICIJOffshoreLeaksScraper
from scrappers.world_bank import WorldBankScraper

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Iniciar FastAPI
app = FastAPI()

# Añadir políticas de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_rate_limit_headers(request: Request, call_next):
    response = await call_next(request)

    if hasattr(request.state, 'rate_limit'):
        rate_info = request.state.rate_limit
        response.headers["X-RateLimit-Limit"] = str(rate_info['limit'])
        response.headers["X-RateLimit-Remaining"] = str(rate_info['remaining'])
        response.headers["X-RateLimit-Reset"] = str(rate_info['reset'])

    return response

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail if isinstance(exc.detail, str) else exc.detail.get("error", "Error"),
            "detail": exc.detail if isinstance(exc.detail, str) else exc.detail.get("message", ""),
            "timestamp": datetime.now().isoformat()
        },
        headers=getattr(exc, 'headers', None)
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "timestamp": datetime.now().isoformat()
        }
    )

async def run_in_executor(func, *args):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, func, *args)


# Estado endpoint
@app.get("/health", response_model=HealthCheckResponse, tags=["General"])
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }


# Búsqueda individual OFAC
@app.post(
    "/api/v1/search/ofac",
    response_model=SearchResponse,
    tags=["Search"]
)
async def search_ofac_endpoint(
    request: Request,
    search_request: EntitySearchRequest,
    api_key: str = Depends(get_api_key)
):
    try:
        await check_rate_limit(request, api_key)

        logger.info(f"OFAC search request for: {search_request.entity_name}")

        result = await run_in_executor(search_ofac, search_request.entity_name)

        if result["hits"] > 0:
            message = f"Se encontraron {result['hits']} resultado(s) para '{search_request.entity_name}' en OFAC"
        else:
            message = f"No se encontraron resultados para '{search_request.entity_name}' en OFAC"

        return SearchResponse(
            source=result["source"],
            query=result["query"],
            hits=result["hits"],
            results=result["results"],
            timestamp=datetime.now().isoformat(),
            message=message
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in OFAC search: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching OFAC: {str(e)}"
        )


# Búsqueda Individual Offshore Leaks endpoint
@app.post(
    "/api/v1/search/offshore-leaks",
    response_model=SearchResponse,
    tags=["Search"]
)
async def search_offshore_leaks_endpoint(
    request: Request,
    search_request: EntitySearchRequest,
    api_key: str = Depends(get_api_key)
):
    try:
        await check_rate_limit(request, api_key)

        logger.info(f"Offshore Leaks search request for: {search_request.entity_name}")

        scraper = ICIJOffshoreLeaksScraper(headless=True)

        entities, challenge = await run_in_executor(
            scraper.scrape_search_results,
            search_request.entity_name,
            2 
        )

        results = []
        for entity in entities:
            results.append({
                "entity_name": entity.get("entity_name"),
                "entity_url": entity.get("entity_url"),
                "jurisdiction": entity.get("jurisdiction"),
                "linked_to": entity.get("linked_to"),
                "data_from": entity.get("data_from")
            })

        if len(results) > 0:
            message = f"Se encontraron {len(results)} resultado(s) para '{search_request.entity_name}' en ICIJ Offshore Leaks"
        else:
            message = f"No se encontraron resultados para '{search_request.entity_name}' en ICIJ Offshore Leaks"

        return SearchResponse(
            source="ICIJ Offshore Leaks",
            query=search_request.entity_name,
            hits=len(results),
            results=results,
            timestamp=datetime.now().isoformat(),
            message=message,
            error="Human verification challenge detected" if challenge else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in Offshore Leaks search: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching Offshore Leaks: {str(e)}"
        )


# Búsqueda Individual World Bank endpoint
@app.post(
    "/api/v1/search/world-bank",
    response_model=SearchResponse,
    tags=["Search"]
)
async def search_world_bank_endpoint(
    request: Request,
    search_request: EntitySearchRequest,
    api_key: str = Depends(get_api_key)
):
    try:
        # Validar el rate limit de max 20 per minuto
        await check_rate_limit(request, api_key)

        logger.info(f"World Bank search request for: {search_request.entity_name}")
        scraper = WorldBankScraper()
        all_firms = await run_in_executor(scraper.scrape)
        if all_firms:
            filtered_firms = scraper.filter_by_name(search_request.entity_name, all_firms)
        else:
            filtered_firms = []
        results = []
        for firm in filtered_firms:
            results.append({
                "firm_name": firm.get("SUPP_NAME"),
                "address": firm.get("SUPP_ADDR"),
                "country": firm.get("COUNTRY_NAME"),
                "from_date": firm.get("DEBAR_FROM_DATE"),
                "to_date": firm.get("DEBAR_TO_DATE"),
                "grounds": firm.get("DEBAR_REASON")
            })

        if len(results) > 0:
            message = f"Se encontraron {len(results)} resultado(s) para '{search_request.entity_name}' en World Bank"
        else:
            message = f"No se encontraron resultados para '{search_request.entity_name}' en World Bank"

        return SearchResponse(
            source="World Bank Debarred Firms",
            query=search_request.entity_name,
            hits=len(results),
            results=results,
            timestamp=datetime.now().isoformat(),
            message=message
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in World Bank search: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching World Bank: {str(e)}"
        )


# Búsqueda en la todas las fuentes previstas.
@app.post(
    "/api/v1/search/all",
    response_model=MultiSourceSearchResponse,
    tags=["Search"]
)
async def search_all_sources_endpoint(
    request: Request,
    search_request: EntitySearchRequest,
    api_key: str = Depends(get_api_key)
):
    try:
        await check_rate_limit(request, api_key)
        async def search_ofac_internal():
            try:
                result = await run_in_executor(search_ofac, search_request.entity_name)
                if result["hits"] > 0:
                    message = f"Se encontraron {result['hits']} resultado(s) en OFAC"
                else:
                    message = f"No se encontraron resultados en OFAC"
                return SearchResponse(
                    source=result["source"],
                    query=result["query"],
                    hits=result["hits"],
                    results=result["results"],
                    timestamp=datetime.now().isoformat(),
                    message=message
                )
            except Exception as e:
                logger.error(f"Error in OFAC search: {str(e)}")
                return SearchResponse(
                    source="OFAC",
                    query=search_request.entity_name,
                    hits=0,
                    results=[],
                    timestamp=datetime.now().isoformat(),
                    error=str(e)
                )

        async def search_offshore_internal():
            try:
                scraper = ICIJOffshoreLeaksScraper(headless=True)
                entities, challenge = await run_in_executor(
                    scraper.scrape_search_results,
                    search_request.entity_name,
                    2 
                )

                results = []
                for entity in entities:
                    results.append({
                        "entity_name": entity.get("entity_name"),
                        "entity_url": entity.get("entity_url"),
                        "jurisdiction": entity.get("jurisdiction"),
                        "linked_to": entity.get("linked_to"),
                        "data_from": entity.get("data_from")
                    })

                if len(results) > 0:
                    message = f"Se encontraron {len(results)} resultado(s) en ICIJ Offshore Leaks"
                else:
                    message = f"No se encontraron resultados en ICIJ Offshore Leaks"

                return SearchResponse(
                    source="ICIJ Offshore Leaks",
                    query=search_request.entity_name,
                    hits=len(results),
                    results=results,
                    timestamp=datetime.now().isoformat(),
                    message=message,
                    error="Human verification challenge detected" if challenge else None
                )
            except Exception as e:
                logger.error(f"Error in Offshore Leaks search: {str(e)}")
                return SearchResponse(
                    source="ICIJ Offshore Leaks",
                    query=search_request.entity_name,
                    hits=0,
                    results=[],
                    timestamp=datetime.now().isoformat(),
                    error=str(e)
                )

        async def search_worldbank_internal():
            try:
                scraper = WorldBankScraper()
                all_firms = await run_in_executor(scraper.scrape)

                if all_firms:
                    filtered_firms = scraper.filter_by_name(search_request.entity_name, all_firms)
                else:
                    filtered_firms = []

                results = []
                for firm in filtered_firms:
                    results.append({
                        "firm_name": firm.get("SUPP_NAME"),
                        "address": firm.get("SUPP_ADDR"),
                        "country": firm.get("COUNTRY_NAME"),
                        "from_date": firm.get("DEBAR_FROM_DATE"),
                        "to_date": firm.get("DEBAR_TO_DATE"),
                        "grounds": firm.get("DEBAR_REASON")
                    })

                if len(results) > 0:
                    message = f"Se encontraron {len(results)} resultado(s) en World Bank"
                else:
                    message = f"No se encontraron resultados en World Bank"

                return SearchResponse(
                    source="World Bank Debarred Firms",
                    query=search_request.entity_name,
                    hits=len(results),
                    results=results,
                    timestamp=datetime.now().isoformat(),
                    message=message
                )
            except Exception as e:
                logger.error(f"Error in World Bank search: {str(e)}")
                return SearchResponse(
                    source="World Bank Debarred Firms",
                    query=search_request.entity_name,
                    hits=0,
                    results=[],
                    timestamp=datetime.now().isoformat(),
                    error=str(e)
                )

        sources = await asyncio.gather(
            search_ofac_internal(),
            search_offshore_internal(),
            search_worldbank_internal()
        )

        total_hits = sum(source.hits for source in sources)

        return MultiSourceSearchResponse(
            query=search_request.entity_name,
            total_hits=total_hits,
            sources=sources,
            timestamp=datetime.now().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in multi-source search: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in multi-source search: {str(e)}"
        )


# Rate Limit Status
@app.get(
    "/api/v1/rate-limit",
    tags=["General"]
)
async def get_rate_limit_status(api_key: str = Depends(get_api_key)):
    rate_info = rate_limiter.get_rate_limit_info(api_key)

    return {
        "api_key": f"{api_key[:8]}...{api_key[-4:]}",
        "rate_limit": rate_info,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
