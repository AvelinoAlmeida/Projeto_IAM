#!/usr/bin/env python3
"""
JML — Leaver: desativa um utilizador, remove todas as roles e revoga sessões.

Uso:
    python leaver.py --username alice
"""

import argparse

import httpx

from _keycloak_client import ADMIN_API, admin_headers, get_user_id


def leaver(username: str) -> None:
    headers = admin_headers()

    print(f"[LEAVER] Desativar utilizador: {username}")

    user_id = get_user_id(username, headers)

    # Desativar conta
    resp = httpx.put(
        f"{ADMIN_API}/users/{user_id}",
        headers=headers,
        json={"enabled": False},
    )
    resp.raise_for_status()
    print(f"[LEAVER] Conta desativada (enabled=false).")

    # Obter roles atuais
    resp = httpx.get(f"{ADMIN_API}/users/{user_id}/role-mappings/realm", headers=headers)
    resp.raise_for_status()
    roles = [r for r in resp.json() if not r.get("composite", False)]

    if roles:
        resp = httpx.delete(
            f"{ADMIN_API}/users/{user_id}/role-mappings/realm",
            headers=headers,
            json=[{"id": r["id"], "name": r["name"]} for r in roles],
        )
        resp.raise_for_status()
        removed = [r["name"] for r in roles]
        print(f"[LEAVER] Roles removidas: {removed}")
    else:
        print("[LEAVER] Sem roles para remover.")

    # Revogar todas as sessões ativas
    resp = httpx.post(f"{ADMIN_API}/users/{user_id}/logout", headers=headers)
    if resp.status_code not in (200, 204):
        print(f"[LEAVER] Aviso: não foi possível revogar sessões (HTTP {resp.status_code}).")
    else:
        print("[LEAVER] Sessões ativas revogadas.")

    print(f"[LEAVER] Concluído. {username} não conseguirá mais autenticar-se.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="JML Leaver — desativa utilizador no Keycloak")
    parser.add_argument("--username", required=True)
    args = parser.parse_args()

    leaver(args.username)
