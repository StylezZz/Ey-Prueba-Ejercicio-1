from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from typing import Optional
import secrets
import hashlib
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY_NAME = "X-API-KEY"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def load_api_from_env()-> dict:
    keys = {}
    i=1
    while True:
        apiKey = os.getenv(f"API_KEY_{i}")
        if not apiKey:
            break
        keys[hashlib.sha256(apiKey.encode()).hexdigest()] = {
            "name": os.getenv(f"API_KEY_NAME_{i}", f"User {i}"),
            "email": os.getenv(f"API_KEY_EMAIL_{i}", f"User{i}@example.com"),
            "active": os.getenv(f"API_KEY_ACTIVE_{i}", "true").lower() == "true"
        }
        i += 1
    return keys


VALID_API_KEYS = load_api_from_env()

def generateApiKey()-> str:
    return secrets.token_urlsafe(32)

def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()

def verify_api_key(api_key: Optional[str])-> dict:
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key is required. Please provide a valid API key in the X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    api_key_hash = hash_api_key(api_key)

    # Validación del API key
    if api_key_hash not in VALID_API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API Key. Please check your credentials.",
        )

    user_info = VALID_API_KEYS[api_key_hash]

    if not user_info.get("active", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API Key has been deactivated. Please contact support.",
        )

    return user_info


async def get_api_key(api_key_header: Optional[str] = Security(api_key_header)) -> str:
    verify_api_key(api_key_header)
    return api_key_header


def add_api_key(api_key: str, name: str, email: str) -> bool:
    api_key_hash = hash_api_key(api_key)
    VALID_API_KEYS[api_key_hash] = {
        "name": name,
        "email": email,
        "active": True
    }
    return True


def revoke_api_key(api_key: str) -> bool:
    api_key_hash = hash_api_key(api_key)
    if api_key_hash in VALID_API_KEYS:
        VALID_API_KEYS[api_key_hash]["active"] = False
        return True
    return False
