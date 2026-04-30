#!/usr/bin/env python3
"""
JML — Joiner: cria um novo utilizador no Keycloak e atribui role + grupo inicial.

Uso:
    python joiner.py --username alice --email alice@empresa.pt --role colaborador
    python joiner.py --username bob --email bob@empresa.pt --role admin
"""

import argparse

import httpx

from _keycloak_client import ADMIN_API, admin_headers, get_group_id, get_role_id

ROLE_TO_GROUP = {
    "admin": "Admins",
    "colaborador": "Colaboradores",
    "visitante": "Visitantes",
}


def joiner(username: str, email: str, role: str, temp_password: str = "Temp@1234") -> None:
    headers = admin_headers()

    print(f"[JOINER] Criar utilizador: {username} | role: {role}")

    role_id = get_role_id(role, headers)
    group_name = ROLE_TO_GROUP.get(role)
    if not group_name:
        raise SystemExit(f"[ERRO] Role '{role}' não mapeada para nenhum grupo.")
    group_id = get_group_id(group_name, headers)

    user_payload = {
        "username": username,
        "email": email,
        "firstName": username.capitalize(),
        "lastName": "Novo",
        "enabled": True,
        "emailVerified": True,
        "requiredActions": [],
        "credentials": [{"type": "password", "value": temp_password, "temporary": False}],
    }

    resp = httpx.post(f"{ADMIN_API}/users", headers=headers, json=user_payload)
    if resp.status_code == 409:
        raise SystemExit(f"[ERRO] Utilizador '{username}' já existe.")
    resp.raise_for_status()

    location = resp.headers.get("Location", "")
    user_id = location.rstrip("/").split("/")[-1]
    print(f"[JOINER] Utilizador criado — ID: {user_id}")

    resp = httpx.post(
        f"{ADMIN_API}/users/{user_id}/role-mappings/realm",
        headers=headers,
        json=[{"id": role_id, "name": role}],
    )
    resp.raise_for_status()
    print(f"[JOINER] Role '{role}' atribuída.")

    resp = httpx.put(f"{ADMIN_API}/users/{user_id}/groups/{group_id}", headers=headers)
    resp.raise_for_status()
    print(f"[JOINER] Grupo '{group_name}' atribuído.")

    print(f"[JOINER] Concluído. {username} pode fazer login com a password '{temp_password}'.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="JML Joiner — cria novo utilizador no Keycloak")
    parser.add_argument("--username", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--role", required=True, choices=["admin", "colaborador", "visitante"])
    parser.add_argument("--password", default="Temp@1234", help="Password temporária inicial")
    args = parser.parse_args()

    joiner(args.username, args.email, args.role, args.password)
