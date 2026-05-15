# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

IAM TP — an Identity and Access Management platform demonstrating OIDC/OAuth2, RBAC, MFA/TOTP, audit logging, and JML (Joiner-Mover-Leaver) user lifecycle management. Stack: Keycloak 26, PostgreSQL 16, FastAPI (Python 3.12).

## Running the Application

The full stack runs via Docker Compose (requires a `.env` file — copy `.env.example` as a starting point):

```bash
docker compose up --build
```

Services after startup (~2–3 min for Keycloak):
- FastAPI + Swagger UI: http://localhost:8000/docs
- Dashboard UI: http://localhost:8000/dashboard
- Keycloak Admin Console: http://localhost:8081

To run FastAPI locally (without Docker), install deps and start uvicorn:

```bash
pip install -r app/requirements.txt
cd app && uvicorn main:app --reload
```

## Running Tests

Tests do not require live services — they mock JWKS with RSA key generation:

```bash
pip install -r tests/requirements.txt
python -m pytest tests/ -v
```

Expected: 4 tests passing in `tests/test_auth.py`.

## Architecture

### Request Flow

```
Client → FastAPI (:8000) → Keycloak (:8080) → PostgreSQL (:5432)
```

JWT tokens are issued by Keycloak (RS256), validated by FastAPI via cached JWKS. Roles are embedded in `realm_access.roles` claim.

### FastAPI App (`app/`)

- **`main.py`** — app setup, CORS, static files, router mounting
- **`config.py`** — all configuration via `pydantic-settings` (loaded from `.env`)
- **`auth.py`** — JWT validation, JWKS caching, `require_role()` and `require_mfa()` FastAPI dependencies
- **`routes/public.py`** — open endpoints: `/health`, `/auth/token`, `/auth/demo-admin-token`, `/me`, `/dashboard`
- **`routes/colaborador.py`** — endpoints requiring `colaborador` or `admin` role
- **`routes/admin.py`** — endpoints requiring `admin` role; includes audit log, user management, MFA-area, and JML REST endpoints

### Authentication & RBAC

`require_role(*roles)` and `require_mfa()` in `auth.py` are FastAPI dependency functions applied per route. MFA is verified by checking for `"otp"`, `"mfa"`, or `"2fa"` in the token's `acr` or `amr` claims.

### JML Lifecycle (`jml/`)

Can be run as standalone CLI scripts or triggered via REST endpoints under `/admin/jml/*`:
- **`joiner.py`** — creates a user, assigns role, adds to group
- **`mover.py`** — changes role, revokes sessions, updates group membership
- **`leaver.py`** — disables account, removes roles, revokes sessions
- **`_keycloak_client.py`** — synchronous Keycloak Admin REST API client used by the scripts

### Keycloak Realm

`realm-export.json` is auto-imported on container startup. Realm: `iam-tp`. Predefined users: `admin.user`, `colaborador.user`, `visitante.user`. Roles: `admin`, `colaborador`, `visitante`. Admin users require TOTP.

## Key Environment Variables

| Variable | Purpose |
|---|---|
| `KEYCLOAK_ADMIN` / `KEYCLOAK_ADMIN_PASSWORD` | Keycloak admin credentials |
| `OIDC_CLIENT_ID` / `OIDC_CLIENT_SECRET` | FastAPI client credentials in Keycloak |
| `DEMO_ADMIN_USER` / `DEMO_ADMIN_PASS` | Demo admin account for `/auth/demo-admin-token` |
| `DB_PASSWORD` | PostgreSQL password |
| `KEYCLOAK_ISSUER_URL` | External Keycloak URL used for JWT issuer validation (differs from internal Docker URL) |
