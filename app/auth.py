from typing import Annotated

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from config import settings

bearer_scheme = HTTPBearer()

_jwks_cache: dict | None = None


async def _get_jwks() -> dict:
    global _jwks_cache
    if _jwks_cache is None:
        async with httpx.AsyncClient() as client:
            resp = await client.get(settings.jwks_uri)
            resp.raise_for_status()
            _jwks_cache = resp.json()
    return _jwks_cache


def _resolve_jwk(token: str, jwks: dict) -> dict:
    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    if not kid:
        raise JWTError("Token sem kid no header")

    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key

    raise JWTError("JWK para o token não encontrada")


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
) -> dict:
    token = credentials.credentials
    try:
        jwks = await _get_jwks()
        jwk = _resolve_jwk(token, jwks)
        payload = jwt.decode(
            token,
            jwk,
            algorithms=["RS256"],
            issuer=settings.issuer,
            options={"verify_aud": False},
        )
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token inválido: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )

def require_mfa():
    async def dependency(user: Annotated[dict, Depends(get_current_user)]) -> dict:
        amr = user.get("amr", [])
        if isinstance(amr, str):
            amr = [amr]

        acr = str(user.get("acr", "")).lower()
        mfa_factors = {"otp", "mfa", "2fa", "password+otp", "google_authenticator"}
        if not any(f in amr for f in mfa_factors) and not any(token in acr for token in mfa_factors):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado. Autenticação multifator (MFA) é necessária para este recurso.",
            )
        return user

    return dependency

def require_role(*roles: str):
    async def dependency(user: Annotated[dict, Depends(get_current_user)]) -> dict:
        user_roles: list[str] = user.get("realm_access", {}).get("roles", [])
        if not any(r in user_roles for r in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acesso negado. Roles necessárias: {list(roles)}. As tuas roles: {user_roles}",
            )
        return user

    return dependency
