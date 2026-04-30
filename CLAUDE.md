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

> **First startup takes 2–3 minutes.** Keycloak has a 90-second `start_period` before health checks begin; the FastAPI container waits for Keycloak to be healthy before it accepts connections.

Services after startup:
- Keycloak admin console: `http://localhost:8081`
- FastAPI + Swagger UI: `http://localhost:8000/docs`
- Interactive dashboard: `http://localhost:8000/dashboard`

### Run Tests

```bash
pip install -r requirements-dev.txt
python -m pytest tests/
# Single test
python -m pytest tests/test_auth.py::test_require_role_allows_admin
```

Tests in `tests/test_auth.py` cover JWT validation (using a generated RSA key pair), `require_role()`, and `require_mfa()`. No running services needed — JWKS fetching is mocked by patching `auth._get_jwks` with `unittest.mock.patch.object`.

> **Note:** `requirements-dev.txt` only pins `pytest`. The tests also require `cryptography` and `python-jose[cryptography]` (used by `app/requirements.txt`). Install `app/requirements.txt` alongside `requirements-dev.txt` to run the full test suite.

### JML Scripts (run locally with Python 3.12+)

Python 3.12 is the minimum tested version. `jml/requirements.txt` does not pin the interpreter — ensure your local `python` resolves to 3.12+ before running.

```bash
cd jml
pip install -r requirements.txt

python joiner.py --username alice --email alice@empresa.pt --role colaborador
python mover.py --username alice --old-role colaborador --new-role admin
python leaver.py --username alice
```

Valid roles: `admin`, `colaborador`, `visitante`.

`jml/_keycloak_client.py` defaults to `KEYCLOAK_URL=http://localhost:8080`, but Keycloak is mapped to port `8081` externally. Set `KEYCLOAK_URL=http://localhost:8081` in your environment or in a `jml/.env` file when running the scripts locally against the Docker stack.

### Get a Bearer Token for Manual Testing

```bash
TOKEN=$(curl -s -X POST http://localhost:8081/realms/iam-tp/protocol/openid-connect/token \
  -d "grant_type=password" -d "client_id=fastapi-client" \
  -d "client_secret=<OIDC_CLIENT_SECRET>" \
  -d "username=colaborador.user" -d "password=Colab@1234" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

Test users: `admin.user`/`Admin@1234` (MFA required), `colaborador.user`/`Colab@1234`, `visitante.user`/`Visit@1234`.

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
3. FastAPI fetches JWKS from Keycloak's OIDC discovery endpoint at startup (cached in memory)
4. `app/auth.py` validates signature, issuer, and audience, then extracts roles
5. `require_role()` or `require_mfa()` dependencies enforce per-endpoint access requirements

### JWKS Caching

`_jwks_cache` in `app/auth.py` is a module-level dict populated on the first token validation and never invalidated. If Keycloak is restarted (e.g., keys rotate), the FastAPI container must also be restarted to refresh the cache — `docker compose restart app` is sufficient.

### FastAPI Route Structure

| Endpoint(s) | File | Required Role |
| --- | --- | --- |
| `/health`, `/public`, `/dashboard`, `/auth/token` | `routes/public.py` | None |
| `/me` | `routes/public.py` | Any valid token |
| `/colaborador/data`, `/colaborador/perfil` | `routes/colaborador.py` | `colaborador` or `admin` |
| `/admin/users`, `/admin/audit`, `/admin/audit/summary` | `routes/admin.py` | `admin` |
| `/admin/mfa-area` | `routes/admin.py` | `admin` + MFA proven |
| `/admin/jml/joiner`, `/admin/jml/mover`, `/admin/jml/leaver` | `routes/admin.py` | `admin` |

`/admin/*` endpoints proxy calls to the Keycloak Admin REST API using a per-request service account token. The `/admin/jml/*` endpoints are API equivalents of the CLI scripts in `jml/`.

`/auth/token` uses the Resource Owner Password Credentials grant (for testing convenience). The Keycloak client also supports Authorization Code + PKCE for browser-based flows.

### MFA Enforcement

`require_mfa()` in `app/auth.py` checks the JWT's `amr` claim (Authentication Methods Reference) for any of: `otp`, `2fa`, `mfa`, `google_authenticator`, or detects `password` + OTP combination. It also checks `acr`. If MFA is not proven, it raises HTTP 403. `admin.user` has `CONFIGURE_TOTP` as a required action in `realm-export.json`, so the Keycloak browser flow forces TOTP enrollment.

### Role-to-Group Mapping

Keycloak groups mirror roles: `admin` → `/Admins`, `colaborador` → `/Colaboradores`, `visitante` → `/Visitantes`. Groups have automatic role assignments; the JML scripts manage both role mappings and group memberships atomically.

This mapping is duplicated in three places — `ROLE_GROUP_MAP` in `app/routes/admin.py` and `ROLE_TO_GROUP` in `jml/joiner.py` and `jml/mover.py`. Adding a new role requires updating all three, plus adding the group and role in `realm-export.json`.

### Key Files

- `app/main.py` — FastAPI app entry point; registers all routers and configures CORS middleware (allowed origins: `http://localhost:8000` and `http://localhost:8080` — update here if testing from other origins)
- `app/config.py` — Pydantic Settings; derives all Keycloak URLs (JWKS, issuer, admin API, token) from base URL + realm name
- `app/auth.py` — JWT validation (`python-jose`), `require_role()`, and `require_mfa()` FastAPI dependencies
- `app/keycloak_client.py` — Async Admin API helpers used by FastAPI routes (`get_admin_token`, `get_user_id`, `get_role`, `get_group_id`). Uses `http://keycloak:8080` (Docker-internal hostname); cannot be called from outside the Docker network.
- `jml/_keycloak_client.py` — Synchronous equivalents for the CLI scripts. Defaults to `http://localhost:8080` (overridable via `KEYCLOAK_URL`). Do not run inside the Docker network without setting `KEYCLOAK_URL=http://keycloak:8080`.
- `app/static/dashboard.html` — Single-page interactive UI for demonstrating auth, RBAC, JML, and audit features
- `realm-export.json` — Versioned Keycloak realm snapshot; auto-imported on container start
- `app/Dockerfile` — Starts uvicorn with `--reload`; Python file changes inside the container are picked up without a restart (useful when bind-mounting `app/` during development)

### Environment Variables

Create a `.env` file at the project root before first run. Required variables:

```ini
KEYCLOAK_ADMIN=admin
KEYCLOAK_ADMIN_PASSWORD=<password>
DB_PASSWORD=<password>
OIDC_CLIENT_ID=fastapi-client
OIDC_CLIENT_SECRET=<secret>   # Must match "secret" for fastapi-client in realm-export.json
```

`docker-compose.yml` maps `OIDC_CLIENT_ID` → `KEYCLOAK_CLIENT_ID` and `OIDC_CLIENT_SECRET` → `KEYCLOAK_CLIENT_SECRET` before passing them to the FastAPI container. The FastAPI `config.py` reads the `KEYCLOAK_*` names.

### Session Revocation

`mover.py` and `leaver.py` (and their API equivalents) explicitly revoke all active Keycloak sessions after role/status changes, so permission changes take effect immediately without waiting for token expiry.
