"""Keycloak Admin REST API client usado pelos scripts JML."""

import os

import httpx
from dotenv import load_dotenv

load_dotenv()

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8080")
REALM = os.getenv("KEYCLOAK_REALM", "iam-tp")
ADMIN_USER = os.getenv("KEYCLOAK_ADMIN", "admin")
ADMIN_PASSWORD = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "")
CLIENT_ID = os.getenv("OIDC_CLIENT_ID", "fastapi-client")
CLIENT_SECRET = os.getenv("OIDC_CLIENT_SECRET", "")

ADMIN_API = f"{KEYCLOAK_URL}/admin/realms/{REALM}"
TOKEN_URL = f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token"


def get_admin_token() -> str:
    resp = httpx.post(
        TOKEN_URL,
        data={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": ADMIN_USER,
            "password": ADMIN_PASSWORD,
        },
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def admin_headers() -> dict:
    return {"Authorization": f"Bearer {get_admin_token()}", "Content-Type": "application/json"}


def get_role_id(role_name: str, headers: dict) -> str:
    resp = httpx.get(f"{ADMIN_API}/roles/{role_name}", headers=headers)
    if resp.status_code == 404:
        raise SystemExit(f"[ERRO] Role '{role_name}' não encontrada no realm.")
    resp.raise_for_status()
    return resp.json()["id"]


def get_user_id(username: str, headers: dict) -> str:
    resp = httpx.get(f"{ADMIN_API}/users", headers=headers, params={"username": username, "exact": "true"})
    resp.raise_for_status()
    users = resp.json()
    if not users:
        raise SystemExit(f"[ERRO] Utilizador '{username}' não encontrado.")
    return users[0]["id"]


def get_group_id(group_name: str, headers: dict) -> str:
    resp = httpx.get(f"{ADMIN_API}/groups", headers=headers, params={"search": group_name})
    resp.raise_for_status()
    groups = resp.json()
    for g in groups:
        if g["name"] == group_name:
            return g["id"]
    raise SystemExit(f"[ERRO] Grupo '{group_name}' não encontrado.")
