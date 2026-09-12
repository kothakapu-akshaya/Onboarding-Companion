"""Onboarding authentication through the existing Corpus API."""

from uuid import UUID

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

security = HTTPBearer(auto_error=False)

CORPUS_AUTH_TIMEOUT = 5.0


async def get_current_onboarding_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> UUID:
    """Resolve the authenticated Corpus user through /auth/me."""

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        async with httpx.AsyncClient(timeout=CORPUS_AUTH_TIMEOUT) as client:
            response = await client.get(
                f"{settings.CORPUS_API_URL.rstrip('/')}/auth/me",
                headers={
                    "Authorization": f"Bearer {credentials.credentials}",
                },
            )
    except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )

    if response.status_code in (401, 403):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if response.status_code >= 500:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = response.json()["id"]
        return UUID(str(user_id))
    except (KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user identity",
            headers={"WWW-Authenticate": "Bearer"},
        )
