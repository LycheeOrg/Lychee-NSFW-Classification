from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from app.config import settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(_api_key_header)) -> None:
    if settings.api_key and api_key != settings.api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
