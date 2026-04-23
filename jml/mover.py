#!/usr/bin/env python3
"""
JML — Mover: altera a role (e grupo) de um utilizador existente e revoga sessões ativas.

Uso:
    python mover.py --username alice --old-role colaborador --new-role admin
"""

import argparse

import httpx

from _keycloak_client import ADMIN_API, admin_headers, get_group_id, get_role_id, get_user_id

ROLE_TO_GROUP = {
    "admin": "Admins",
    "colaborador": "Colaboradores",
    "visitante": "Visitantes",
}


def mover(username: str, old_role: str, new_role: str) -> None:
    headers = admin_headers()

    print(f"[MOVER] Mover {username}: {old_role} → {new_role}")

    user_id = get_user_id(username, headers)
    old_role_id = get_role_id(old_role, headers)
    new_role_id = get_role_id(new_role, headers)
    old_group_id = get_group_id(ROLE_TO_GROUP[old_role], headers)
    new_group_id = get_group_id(ROLE_TO_GROUP[new_role], headers)

    resp = httpx.delete(
        f"{ADMIN_API}/users/{user_id}/role-mappings/realm",
        headers=headers,
        json=[{"id": old_role_id, "name": old_role}],
    )
    resp.raise_for_status()
    print(f"[MOVER] Role '{old_role}' removida.")

    resp = httpx.post(
        f"{ADMIN_API}/users/{user_id}/role-mappings/realm",
        headers=headers,
        json=[{"id": new_role_id, "name": new_role}],
    )
    resp.raise_for_status()
    print(f"[MOVER] Role '{new_role}' atribuída.")

    resp = httpx.delete(f"{ADMIN_API}/users/{user_id}/groups/{old_group_id}", headers=headers)
    resp.raise_for_status()
    print(f"[MOVER] Removido do grupo '{ROLE_TO_GROUP[old_role]}'.")

    resp = httpx.put(f"{ADMIN_API}/users/{user_id}/groups/{new_group_id}", headers=headers)
    resp.raise_for_status()
    print(f"[MOVER] Adicionado ao grupo '{ROLE_TO_GROUP[new_role]}'.")

    # Revogar sessões ativas para forçar novo login com nova role
    resp = httpx.post(f"{ADMIN_API}/users/{user_id}/logout", headers=headers)
    if resp.status_code not in (200, 204):
        print(f"[MOVER] Aviso: não foi possível revogar sessões (HTTP {resp.status_code}).")
    else:
        print("[MOVER] Sessões ativas revogadas — utilizador terá de fazer login novamente.")

    print(f"[MOVER] Concluído. {username} agora tem role '{new_role}'.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="JML Mover — altera role de utilizador no Keycloak")
    parser.add_argument("--username", required=True)
    parser.add_argument("--old-role", required=True, choices=["admin", "colaborador", "visitante"])
    parser.add_argument("--new-role", required=True, choices=["admin", "colaborador", "visitante"])
    args = parser.parse_args()

    mover(args.username, args.old_role, args.new_role)
