import pathlib
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from auth import get_current_user
from config import settings

router = APIRouter(tags=["public"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.get("/health")
async def health():
    return {"status": "ok", "service": "IAM TP — FastAPI"}


@router.get("/public")
async def public_resource():
    return {
        "message": "Este recurso é público — não requer autenticação.",
        "data": ["item_publico_1", "item_publico_2"],
    }


@router.get("/me")
async def me(user: Annotated[dict, Depends(get_current_user)]):
    return {
        "sub": user.get("sub"),
        "email": user.get("email"),
        "preferred_username": user.get("preferred_username"),
        "roles": user.get("realm_access", {}).get("roles", []),
        "name": user.get("name"),
    }


@router.post("/auth/token")
async def login(body: LoginRequest):
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            settings.token_url,
            data={
                "grant_type": "password",
                "client_id": settings.keycloak_client_id,
                "client_secret": settings.keycloak_client_secret,
                "username": body.username,
                "password": body.password,
                "scope": "openid",
            },
        )
    if resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas ou utilizador não encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    data = resp.json()
    return {
        "access_token": data["access_token"],
        "token_type": "bearer",
        "expires_in": data.get("expires_in", 300),
    }


@router.get("/dashboard", include_in_schema=False, response_class=HTMLResponse)
async def dashboard():
    html_path = pathlib.Path(__file__).parent.parent / "static" / "dashboard.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))
