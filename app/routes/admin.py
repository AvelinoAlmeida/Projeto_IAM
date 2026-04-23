from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status

from auth import require_role
from config import settings

router = APIRouter(prefix="/admin", tags=["admin"])

_require_admin = require_role("admin")


async def _get_admin_token() -> str:
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


@router.get("/users")
async def list_users(user: Annotated[dict, Depends(_require_admin)]):
    token = await _get_admin_token()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.admin_api_url}/users",
            headers={"Authorization": f"Bearer {token}"},
            params={"max": 50},
        )
        resp.raise_for_status()
        users = resp.json()

    return {
        "total": len(users),
        "users": [
            {
                "id": u.get("id"),
                "username": u.get("username"),
                "email": u.get("email"),
                "enabled": u.get("enabled"),
                "createdTimestamp": u.get("createdTimestamp"),
            }
            for u in users
        ],
    }


@router.get("/audit")
async def audit_events(
    user: Annotated[dict, Depends(_require_admin)],
    max_events: int = Query(default=50, le=200),
    event_type: str | None = Query(default=None),
):
    token = await _get_admin_token()

    params: dict = {"max": max_events}
    if event_type:
        params["type"] = event_type

    async with httpx.AsyncClient() as client:
        events_resp = await client.get(
            f"{settings.admin_api_url}/events",
            headers={"Authorization": f"Bearer {token}"},
            params=params,
        )
        admin_events_resp = await client.get(
            f"{settings.admin_api_url}/admin-events",
            headers={"Authorization": f"Bearer {token}"},
            params={"max": max_events},
        )
        events_resp.raise_for_status()
        admin_events_resp.raise_for_status()

    return {
        "user_events": events_resp.json(),
        "admin_events": admin_events_resp.json(),
    }


@router.get("/audit/summary")
async def audit_summary(user: Annotated[dict, Depends(_require_admin)]):
    token = await _get_admin_token()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.admin_api_url}/events",
            headers={"Authorization": f"Bearer {token}"},
            params={"max": 200},
        )
        resp.raise_for_status()
        events = resp.json()

    summary: dict[str, int] = {}
    for event in events:
        t = event.get("type", "UNKNOWN")
        summary[t] = summary.get(t, 0) + 1

    return {"total": len(events), "by_type": summary}
