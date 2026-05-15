import pathlib
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from auth import get_current_user
from config import settings
from keycloak_client import admin_headers, get_admin_token, get_group_id, get_role

router = APIRouter(tags=["public"])


class LoginRequest(BaseModel):
    username: str
    password: str
    totp: str | None = None


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
                **({"totp": body.totp} if body.totp else {}),
            },
        )
    if resp.status_code != 200:
        error = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        error_description = error.get("error_description") or error.get("error")
        if error_description and "resolve_required_actions" in error_description:
            detail = "Login bloqueado por ação obrigatória no Keycloak. Recrie o utilizador no JML ou limpe required actions."
        else:
            detail = "Credenciais inválidas ou utilizador não encontrado"
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )
    data = resp.json()
    return {
        "access_token": data["access_token"],
        "token_type": "bearer",
        "expires_in": data.get("expires_in", 300),
    }


@router.post("/auth/demo-admin-token", include_in_schema=False)
async def demo_admin_token():
    """Cria/garante utilizador demo (sem OTP) e devolve token — apenas para demonstração."""
    admin_tkn = await get_admin_token()
    async with httpx.AsyncClient() as client:
        headers = admin_headers(admin_tkn)

        # Verificar se o utilizador demo já existe
        r = await client.get(
            f"{settings.admin_api_url}/users",
            headers=headers,
            params={"username": settings.demo_admin_user, "exact": "true"},
        )
        r.raise_for_status()
        users = r.json()

        if not users:
            # Criar utilizador sem required actions e sem OTP
            cr = await client.post(
                f"{settings.admin_api_url}/users",
                headers=headers,
                json={
                    "username": settings.demo_admin_user,
                    "email": f"{settings.demo_admin_user}@iam-tp.local",
                    "firstName": "Admin",
                    "lastName": "Demo",
                    "enabled": True,
                    "emailVerified": True,
                    "requiredActions": [],
                    "credentials": [{"type": "password", "value": settings.demo_admin_pass, "temporary": False}],
                },
            )
            if cr.status_code not in (200, 201):
                raise HTTPException(status_code=500, detail="Erro ao criar utilizador demo")

            r2 = await client.get(
                f"{settings.admin_api_url}/users",
                headers=headers,
                params={"username": settings.demo_admin_user, "exact": "true"},
            )
            r2.raise_for_status()
            user_id = r2.json()[0]["id"]
        else:
            user_id = users[0]["id"]

        # Garantir role admin (idempotente — não falha se já atribuído)
        role = await get_role(client, headers, "admin")
        assigned = await client.get(
            f"{settings.admin_api_url}/users/{user_id}/role-mappings/realm",
            headers=headers,
        )
        assigned_names = {r["name"] for r in assigned.json()} if assigned.is_success else set()
        if "admin" not in assigned_names:
            await client.post(
                f"{settings.admin_api_url}/users/{user_id}/role-mappings/realm",
                headers=headers,
                json=[role],
            )

        # Garantir grupo Admins (idempotente)
        if not users:
            group_id = await get_group_id(client, headers, "Admins")
            await client.put(
                f"{settings.admin_api_url}/users/{user_id}/groups/{group_id}",
                headers=headers,
            )

        # Obter token via direct grant (sem OTP — utilizador demo não tem OTP configurado)
        tr = await client.post(
            settings.token_url,
            data={
                "grant_type": "password",
                "client_id": settings.keycloak_client_id,
                "client_secret": settings.keycloak_client_secret,
                "username": settings.demo_admin_user,
                "password": settings.demo_admin_pass,
                "scope": "openid",
            },
        )

    if tr.status_code != 200:
        raise HTTPException(status_code=500, detail="Erro ao obter token para utilizador demo")

    data = tr.json()
    return {
        "access_token": data["access_token"],
        "token_type": "bearer",
        "expires_in": data.get("expires_in", 300),
    }


@router.get("/dashboard", include_in_schema=False, response_class=HTMLResponse)
async def dashboard():
    html_path = pathlib.Path(__file__).parent.parent / "static" / "dashboard.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))
