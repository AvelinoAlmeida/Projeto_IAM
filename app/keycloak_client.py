from typing import Any

import httpx
from fastapi import HTTPException, status

from config import settings


async def get_admin_token() -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            settings.token_url,
            data={
                "grant_type": "password",
                "client_id": settings.keycloak_client_id,
                "client_secret": settings.keycloak_client_secret,
                "username": settings.keycloak_admin_user,
                "password": settings.keycloak_admin_password,
                "scope": "openid",
            },
        )
    if resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Não foi possível obter token de admin do Keycloak",
        )
    return resp.json()["access_token"]


def admin_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


async def get_user_id(client: httpx.AsyncClient, headers: dict[str, str], username: str) -> str:
    resp = await client.get(
        f"{settings.admin_api_url}/users",
        headers=headers,
        params={"username": username, "exact": "true"},
    )
    resp.raise_for_status()
    users = resp.json()
    if not users:
        raise HTTPException(status_code=404, detail=f"Utilizador '{username}' não encontrado")
    return users[0]["id"]


async def get_role(client: httpx.AsyncClient, headers: dict[str, str], role_name: str) -> dict[str, Any]:
    resp = await client.get(
        f"{settings.admin_api_url}/roles/{role_name}",
        headers=headers,
    )
    if resp.status_code == 404:
        raise HTTPException(status_code=400, detail=f"Role '{role_name}' não existe")
    resp.raise_for_status()
    return resp.json()


async def get_group_id(client: httpx.AsyncClient, headers: dict[str, str], group_name: str) -> str:
    resp = await client.get(
        f"{settings.admin_api_url}/groups",
        headers=headers,
        params={"search": group_name},
    )
    resp.raise_for_status()
    groups = resp.json()
    if not groups:
        raise HTTPException(status_code=400, detail=f"Grupo '{group_name}' não encontrado")
    return groups[0]["id"]
