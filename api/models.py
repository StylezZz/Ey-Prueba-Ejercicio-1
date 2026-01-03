"""
Modelos para las respuestas y solicitudes de la API
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class EntitySearchRequest(BaseModel):
    """Modelo de solicitud para búsqueda de entidad"""
    entity_name: str = Field(..., min_length=1, max_length=200, description="Nombre de la entidad a buscar")

    class Config:
        json_schema_extra = {
            "example": {
                "entity_name": "London Foundation"
            }
        }


class SearchResponse(BaseModel):
    """Modelo de respuesta de búsqueda"""
    source: str = Field(..., description="Data source name")
    query: str = Field(..., description="Search query used")
    hits: int = Field(..., description="Number of results found")
    results: List[Dict[str, Any]] = Field(..., description="Array of entities found")
    timestamp: str = Field(..., description="Timestamp of the search")
    message: Optional[str] = Field(None, description="Informational message")
    error: Optional[str] = Field(None, description="Error message if any")

    class Config:
        json_schema_extra = {
            "example": {
                "source": "ICIJ Offshore Leaks",
                "query": "London Foundation",
                "hits": 10,
                "results": [
                    {
                        "entity_name": "LONDON FOUNDATION",
                        "jurisdiction": "Panama",
                        "linked_to": "Belize",
                        "data_from": "Panama Papers"
                    }
                ],
                "timestamp": "2026-01-01T12:00:00",
                "error": None
            }
        }


class MultiSourceSearchResponse(BaseModel):
    """Modelo de respuesta para búsqueda en múltiples fuentes"""
    query: str
    total_hits: int
    sources: List[SearchResponse]
    timestamp: str


class ErrorResponse(BaseModel):
    """Respuesta de error estándar"""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error description")
    timestamp: str = Field(..., description="Error timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "Rate limit exceeded",
                "detail": "Maximum 20 requests per minute allowed",
                "timestamp": "2026-01-01T12:00:00"
            }
        }


class HealthCheckResponse(BaseModel):
    """Health check response model"""
    status: str
    timestamp: str
    version: str = "1.0.0"
