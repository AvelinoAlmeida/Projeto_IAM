from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from auth import require_mfa, require_role
from config import settings
from keycloak_client import (
    admin_headers,
    get_admin_token,
    get_group_id,
    get_role,
    get_user_id,
)

router = APIRouter(prefix="/admin", tags=["admin"])

_require_admin = require_role("admin")
_require_mfa = require_mfa()

ROLE_GROUP_MAP = {
    "admin": "Admins",
    "colaborador": "Colaboradores",
    "visitante": "Visitantes",
}


class JoinerRequest(BaseModel):
    username: str
    email: str
    role: str
    password: str = "Temp@1234"


class MoverRequest(BaseModel):
    username: str
    old_role: str
    new_role: str


class LeaverRequest(BaseModel):
    username: str


@router.get("/users")
async def list_users(user: Annotated[dict, Depends(_require_admin)]):
    token = await get_admin_token()
    headers = admin_headers(token)

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.admin_api_url}/users",
            headers=headers,
            params={"max": 50},
        )
        resp.raise_for_status()
        users = resp.json()

        import asyncio

        async def get_user_roles(uid: str) -> list[str]:
            r = await client.get(
                f"{settings.admin_api_url}/users/{uid}/role-mappings/realm",
                headers=headers,
            )
            if not r.is_success:
                return []
            return [
                ro["name"]
                for ro in r.json()
                if not ro.get("composite", False) and ro["name"] in ROLE_GROUP_MAP
            ]

        roles_list = await asyncio.gather(*[get_user_roles(u["id"]) for u in users])

    return {
        "total": len(users),
        "users": [
            {
                "id": u.get("id"),
                "username": u.get("username"),
                "email": u.get("email"),
                "enabled": u.get("enabled"),
                "createdTimestamp": u.get("createdTimestamp"),
                "roles": roles,
            }
            for u, roles in zip(users, roles_list)
        ],
    }


@router.get("/audit")
async def audit_events(
    user: Annotated[dict, Depends(_require_admin)],
    max_events: int = Query(default=50, le=200),
    event_type: str | None = Query(default=None),
):
    token = await get_admin_token()
    headers = admin_headers(token)

    params: dict = {"max": max_events}
    if event_type:
        params["type"] = event_type

    async with httpx.AsyncClient() as client:
        events_resp = await client.get(
            f"{settings.admin_api_url}/events",
            headers=headers,
            params=params,
        )
        admin_events_resp = await client.get(
            f"{settings.admin_api_url}/admin-events",
            headers=headers,
            params={"max": max_events},
        )
        events_resp.raise_for_status()
        admin_events_resp.raise_for_status()

    return {
        "user_events": events_resp.json(),
        "admin_events": admin_events_resp.json(),
    }


@router.get("/mfa-area")
async def mfa_area(
    user: Annotated[dict, Depends(_require_admin)],
    mfa_user: Annotated[dict, Depends(_require_mfa)],
):
    return {
        "message": "Acesso admin com MFA confirmado.",
        "user": mfa_user.get("preferred_username"),
        "amr": mfa_user.get("amr"),
        "acr": mfa_user.get("acr"),
    }


@router.get("/audit/summary")
async def audit_summary(user: Annotated[dict, Depends(_require_admin)]):
    token = await get_admin_token()
    headers = admin_headers(token)
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.admin_api_url}/events",
            headers=headers,
            params={"max": 200},
        )
        resp.raise_for_status()
        events = resp.json()

    summary: dict[str, int] = {}
    for event in events:
        t = event.get("type", "UNKNOWN")
        summary[t] = summary.get(t, 0) + 1

    return {"total": len(events), "by_type": summary}


@router.post("/jml/joiner", status_code=201)
async def jml_joiner(
    body: JoinerRequest,
    user: Annotated[dict, Depends(_require_admin)],
):
    if body.role not in ROLE_GROUP_MAP:
        raise HTTPException(status_code=400, detail=f"Role inválida. Válidas: {list(ROLE_GROUP_MAP)}")

    token = await get_admin_token()
    headers = admin_headers(token)

    parts = body.username.replace("-", ".").replace("_", ".").split(".")
    first_name = parts[0].capitalize() if parts else body.username
    last_name = parts[-1].capitalize() if len(parts) > 1 else ""

    async with httpx.AsyncClient() as client:
        create_resp = await client.post(
            f"{settings.admin_api_url}/users",
            headers=headers,
            json={
                "username": body.username,
                "email": body.email,
                "firstName": first_name,
                "lastName": last_name,
                "emailVerified": True,
                "enabled": True,
                "credentials": [{"type": "password", "value": body.password, "temporary": False}],
                "requiredActions": [],
            },
        )
        if create_resp.status_code not in (201, 204, 409):
            err = create_resp.json() if create_resp.headers.get("content-type", "").startswith("application/json") else {}
            raise HTTPException(
                status_code=400,
                detail=err.get("errorMessage") or err.get("error_description") or err.get("error") or f"Keycloak recusou o utilizador (HTTP {create_resp.status_code})",
            )

        user_id = await get_user_id(client, headers, body.username)
        if create_resp.status_code == 409:
            await client.put(
                f"{settings.admin_api_url}/users/{user_id}",
                headers=headers,
                json={"email": body.email, "firstName": first_name, "lastName": last_name, "enabled": True, "emailVerified": True, "requiredActions": []},
            )
            await client.put(
                f"{settings.admin_api_url}/users/{user_id}/reset-password",
                headers=headers,
                json={"type": "password", "value": body.password, "temporary": False},
            )
        # Remove existing realm roles before assigning the new one
        existing_resp = await client.get(
            f"{settings.admin_api_url}/users/{user_id}/role-mappings/realm",
            headers=headers,
        )
        if existing_resp.is_success:
            existing_roles = [r for r in existing_resp.json() if not r.get("composite", False) and r["name"] in ROLE_GROUP_MAP]
            if existing_roles:
                await client.request(
                    "DELETE",
                    f"{settings.admin_api_url}/users/{user_id}/role-mappings/realm",
                    headers=headers,
                    json=existing_roles,
                )
                for old_r in existing_roles:
                    old_gid = await get_group_id(client, headers, ROLE_GROUP_MAP[old_r["name"]])
                    await client.delete(
                        f"{settings.admin_api_url}/users/{user_id}/groups/{old_gid}",
                        headers=headers,
                    )

        role = await get_role(client, headers, body.role)
        group_id = await get_group_id(client, headers, ROLE_GROUP_MAP[body.role])

        await client.post(
            f"{settings.admin_api_url}/users/{user_id}/role-mappings/realm",
            headers=headers,
            json=[role],
        )
        await client.put(
            f"{settings.admin_api_url}/users/{user_id}/groups/{group_id}",
            headers=headers,
        )

    action = "atualizado" if create_resp.status_code == 409 else "criado"
    return {"ok": True, "user_id": user_id, "message": f"Utilizador '{body.username}' {action} com role '{body.role}'"}


@router.post("/jml/mover")
async def jml_mover(
    body: MoverRequest,
    user: Annotated[dict, Depends(_require_admin)],
):
    for r in (body.old_role, body.new_role):
        if r not in ROLE_GROUP_MAP:
            raise HTTPException(status_code=400, detail=f"Role inválida: '{r}'. Válidas: {list(ROLE_GROUP_MAP)}")

    token = await get_admin_token()
    headers = admin_headers(token)

    async with httpx.AsyncClient() as client:
        user_id = await get_user_id(client, headers, body.username)
        old_role = await get_role(client, headers, body.old_role)
        new_role = await get_role(client, headers, body.new_role)
        old_group_id = await get_group_id(client, headers, ROLE_GROUP_MAP[body.old_role])
        new_group_id = await get_group_id(client, headers, ROLE_GROUP_MAP[body.new_role])

        await client.request(
            "DELETE",
            f"{settings.admin_api_url}/users/{user_id}/role-mappings/realm",
            headers=headers,
            json=[old_role],
        )
        await client.delete(
            f"{settings.admin_api_url}/users/{user_id}/groups/{old_group_id}",
            headers=headers,
        )
        await client.post(
            f"{settings.admin_api_url}/users/{user_id}/role-mappings/realm",
            headers=headers,
            json=[new_role],
        )
        await client.put(
            f"{settings.admin_api_url}/users/{user_id}/groups/{new_group_id}",
            headers=headers,
        )
        await client.delete(
            f"{settings.admin_api_url}/users/{user_id}/sessions",
            headers=headers,
        )

    return {"ok": True, "message": f"'{body.username}' movido de '{body.old_role}' para '{body.new_role}'. Sessões revogadas."}


@router.post("/jml/leaver")
async def jml_leaver(
    body: LeaverRequest,
    user: Annotated[dict, Depends(_require_admin)],
):
    token = await get_admin_token()
    headers = admin_headers(token)

    async with httpx.AsyncClient() as client:
        user_id = await get_user_id(client, headers, body.username)

        await client.put(
            f"{settings.admin_api_url}/users/{user_id}",
            headers=headers,
            json={"enabled": False},
        )

        roles_resp = await client.get(
            f"{settings.admin_api_url}/users/{user_id}/role-mappings/realm",
            headers=headers,
        )
        roles_resp.raise_for_status()
        roles = [r for r in roles_resp.json() if not r.get("composite", False)]

        if roles:
            await client.request(
                "DELETE",
                f"{settings.admin_api_url}/users/{user_id}/role-mappings/realm",
                headers=headers,
                json=roles,
            )

        await client.delete(
            f"{settings.admin_api_url}/users/{user_id}/sessions",
            headers=headers,
        )

    return {"ok": True, "message": f"Utilizador '{body.username}' desativado. Roles removidas. Sessões revogadas."}
