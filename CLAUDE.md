# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Identity and Access Management (IAM) practical assignment (TP) for MEI-ESTG-IPP. Three-service architecture:
- **Keycloak 26** — OIDC/OAuth2 identity provider, auto-imports realm from `realm-export.json`
- **PostgreSQL 16** — Keycloak's database backend
- **FastAPI** — Protected REST API validating Keycloak-issued JWTs (RS256) and enforcing RBAC

## Development Commands

```bash
# Start all services (first-time or after code changes)
docker compose up --build

# Start without rebuilding images
docker compose up
```

Services after startup:
- Keycloak admin console: `http://localhost:8081`
- FastAPI + Swagger UI: `http://localhost:8000/docs`

### JML Scripts (run locally with Python 3.12+)

```bash
cd jml
pip install -r requirements.txt

python joiner.py --username alice --email alice@empresa.pt --role colaborador
python mover.py --username alice --old-role colaborador --new-role admin
python leaver.py --username alice
```

Valid roles: `admin`, `colaborador`, `visitante`.

### Get a Bearer Token for Manual Testing

```bash
TOKEN=$(curl -s -X POST http://localhost:8081/realms/iam-tp/protocol/openid-connect/token \
  -d "grant_type=password" -d "client_id=fastapi-client" \
  -d "client_secret=<OIDC_CLIENT_SECRET>" \
  -d "username=colaborador.user" -d "password=Colab@1234" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

Test users: `admin.user`/`Admin@1234` (MFA), `colaborador.user`/`Colab@1234`, `visitante.user`/`Visit@1234`.

### Re-export Realm After Manual Keycloak Changes

```bash
docker exec -it <keycloak-container-id> \
  /opt/keycloak/bin/kc.sh export --realm iam-tp --file /tmp/realm-export.json
docker cp <keycloak-container-id>:/tmp/realm-export.json ./realm-export.json
```

## Architecture

### Authentication Flow

1. Client authenticates against Keycloak (`localhost:8081/realms/iam-tp`)
2. Keycloak returns JWT signed with RS256; roles are embedded in `realm_access.roles`
3. FastAPI fetches public keys from Keycloak's JWKS endpoint at startup
4. `app/auth.py` validates signature, issuer, and audience, then extracts roles
5. `require_role()` dependency enforces per-endpoint role requirements

### FastAPI Route Structure

| Prefix | File | Required Role |
|--------|------|--------------|
| `/health`, `/public` | `routes/public.py` | None |
| `/me` | `routes/public.py` | Any valid token |
| `/colaborador/*` | `routes/colaborador.py` | `colaborador` or `admin` |
| `/admin/*` | `routes/admin.py` | `admin` only |

Admin endpoints (`/admin/users`, `/admin/audit`, `/admin/audit/summary`) proxy calls to the Keycloak Admin REST API using a service account token acquired per-request.

### Key Files

- `app/config.py` — Pydantic Settings; derives all Keycloak URLs from base URL + realm name
- `app/auth.py` — JWT validation (`python-jose`) and `require_role()` FastAPI dependency
- `jml/_keycloak_client.py` — Shared admin API client used by all three JML scripts
- `realm-export.json` — Versioned Keycloak realm snapshot; auto-imported on container start

### Environment Variables

Copy `.env.example` → `.env` before first run. Critical variables:
- `OIDC_CLIENT_SECRET` — Must match the value in `realm-export.json` for `fastapi-client`
- `KEYCLOAK_ADMIN` / `KEYCLOAK_ADMIN_PASSWORD` — Keycloak admin credentials
- `DB_PASSWORD` — PostgreSQL password

### Session Revocation

`mover.py` and `leaver.py` explicitly revoke all active Keycloak sessions after role/status changes, so permission changes take effect immediately without waiting for token expiry.
