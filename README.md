# IAM TP — Gestão de Identidade e Acesso

**UC:** Gestão de Identidade · MEI, ESTG-IPP · 2025/2026  
**Stack:** Keycloak 26 · PostgreSQL 16 · Python 3.12 · FastAPI

Plataforma **IAM** containerizada que demonstra autenticação OIDC/OAuth2, RBAC, MFA/TOTP, ciclo de vida JML e auditoria de eventos, integrados através do Keycloak como Identity Provider.

---

## Arranque Rápido

**Pré-requisitos:** Docker Desktop · Python 3.12+ (apenas para scripts JML e testes)

### 1. Criar `.env` na raiz do projeto

```ini
KEYCLOAK_ADMIN=admin
KEYCLOAK_ADMIN_PASSWORD=Admin123!
DB_PASSWORD=Admin123!
OIDC_CLIENT_ID=fastapi-client
OIDC_CLIENT_SECRET=Admin123!
```

> `OIDC_CLIENT_SECRET` deve coincidir com o campo `"secret"` de `fastapi-client` em `realm-export.json`.

### 2. Iniciar os serviços

```bash
docker compose up --build
```

O arranque completo demora **2–3 minutos** (Keycloak tem 90 s de startup). Aguardar:

```text
keycloak  | Listening on: http://0.0.0.0:8080
app       | Application startup complete.
```

| Serviço | URL |
|---|---|
| FastAPI + Swagger UI | `http://localhost:8000/docs` |
| Dashboard interativo | `http://localhost:8000/dashboard` |
| Keycloak Admin Console | `http://localhost:8081` |

### Utilizadores de Teste

| Username | Password | Role | Notas |
|---|---|---|---|
| `admin.user` | `Admin@1234` | admin | MFA (TOTP) obrigatório no 1.º login |
| `colaborador.user` | `Colab@1234` | colaborador | — |
| `visitante.user` | `Visit@1234` | visitante | — |

---

## Critérios de Avaliação

| Critério | Secção | Peso |
|---|---|---:|
| Arquitetura e coerência técnica | [Arquitetura](#arquitetura) | 20% |
| Autenticação / Federação OIDC | [Autenticação OIDC](#1-autenticação-oidc-e-jwt) | 15% |
| Autorização por papéis (RBAC) | [Autorização RBAC](#2-autorização-rbac) | 15% |
| MFA (TOTP) | [MFA / TOTP](#3-mfa--totp) | 15% |
| Ciclo de vida JML | [JML](#4-ciclo-de-vida-jml) | 15% |
| Auditoria e segurança operacional | [Auditoria](#5-auditoria) | 10% |
| Qualidade da demo | Dashboard · `http://localhost:8000/dashboard` | 10% |

---

## Arquitetura

```text
┌─────────────────────────────── Docker Compose ───────────────────────────────┐
│                                                                               │
│   ┌─────────────────────┐   OIDC / JWT   ┌───────────────────────────────┐  │
│   │      FastAPI         │◄──────────────►│          Keycloak 26          │  │
│   │      :8000           │                │   :8080 interno · :8081 ext.  │  │
│   │                      │                │                               │  │
│   │  /public  (sem auth) │                │  Realm: iam-tp                │  │
│   │  /me      (token)    │                │  Roles: admin, colaborador,   │  │
│   │  /colaborador (RBAC) │                │         visitante             │  │
│   │  /admin   (RBAC+MFA) │                │  MFA: TOTP obrigatório(admin) │  │
│   └─────────────────────┘                └───────────────┬───────────────┘  │
│                                                           │                   │
│   ┌──────────────────────────────────────┐               │ Admin API         │
│   │  JML Scripts (Python CLI)            │──────────────►│                   │
│   │  joiner.py · mover.py · leaver.py   │               ▼                   │
│   └──────────────────────────────────────┘  ┌────────────────────────────┐  │
│                                              │      PostgreSQL 16          │  │
│                                              │  (base de dados Keycloak)  │  │
│                                              └────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────────┘
```

**Fluxo de autenticação:**

1. Cliente autentica no Keycloak → recebe JWT assinado (RS256)
2. JWT contém roles em `realm_access.roles`
3. FastAPI valida assinatura via JWKS (cache em memória), extrai roles, aplica RBAC
4. `require_role()` / `require_mfa()` protegem os endpoints

**Ficheiros-chave:**

| Ficheiro | Responsabilidade |
|---|---|
| `app/auth.py` | Validação JWT (RS256), `require_role()`, `require_mfa()` |
| `app/config.py` | Pydantic Settings — URLs derivadas de `KEYCLOAK_URL` |
| `app/keycloak_client.py` | Helpers async para Admin REST API (uso interno Docker) |
| `app/routes/admin.py` | Endpoints `/admin/*` + JML REST |
| `jml/_keycloak_client.py` | Cliente síncrono para scripts CLI locais |
| `realm-export.json` | Snapshot do realm, auto-importado em cada `docker compose up` |

---

## Preparação dos Tokens de Demo

Obter tokens para os três roles **uma vez**, antes de testar os critérios abaixo:

```bash
# Colaborador
TOKEN_COLAB=$(curl -s -X POST http://localhost:8081/realms/iam-tp/protocol/openid-connect/token \
  -d "grant_type=password" -d "client_id=fastapi-client" -d "client_secret=Admin123!" \
  -d "username=colaborador.user" -d "password=Colab@1234" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Admin
TOKEN_ADMIN=$(curl -s -X POST http://localhost:8081/realms/iam-tp/protocol/openid-connect/token \
  -d "grant_type=password" -d "client_id=fastapi-client" -d "client_secret=Admin123!" \
  -d "username=admin.user" -d "password=Admin@1234" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Visitante
TOKEN_VISIT=$(curl -s -X POST http://localhost:8081/realms/iam-tp/protocol/openid-connect/token \
  -d "grant_type=password" -d "client_id=fastapi-client" -d "client_secret=Admin123!" \
  -d "username=visitante.user" -d "password=Visit@1234" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

**PowerShell (alternativa):**
```powershell
$body = @{ username = "colaborador.user"; password = "Colab@1234" } | ConvertTo-Json
Invoke-WebRequest -Uri http://localhost:8000/auth/token `
  -Method POST -ContentType "application/json" -Body $body -UseBasicParsing
```

> `/auth/token` usa o grant *Resource Owner Password Credentials* (atalho de teste). Em produção o fluxo recomendado é *Authorization Code + PKCE*, também suportado pelo cliente `fastapi-client`.

---

## 1. Autenticação OIDC e JWT

### Inspecionar o JWT

```bash
echo $TOKEN_COLAB | python3 -c "
import sys, base64, json
payload = sys.stdin.read().strip().split('.')[1]
payload += '=' * (4 - len(payload) % 4)
print(json.dumps(json.loads(base64.urlsafe_b64decode(payload)), indent=2))
"
```

Campos relevantes no payload:

```json
{
  "iss": "http://keycloak:8080/realms/iam-tp",
  "preferred_username": "colaborador.user",
  "realm_access": { "roles": ["colaborador", "default-roles-iam-tp"] },
  "amr": ["password"]
}
```

### Verificar identidade

```bash
curl -s -H "Authorization: Bearer $TOKEN_COLAB" http://localhost:8000/me | python3 -m json.tool
```

```json
{
  "sub": "...",
  "preferred_username": "colaborador.user",
  "email": "colaborador@empresa.pt",
  "roles": ["colaborador"]
}
```

### Rejeição de tokens inválidos

```bash
# Token inválido → 401
curl -s -H "Authorization: Bearer token_invalido" http://localhost:8000/me
# → {"detail":"Token inválido"}

# Sem token → 401
curl -s http://localhost:8000/me
# → {"detail":"Not authenticated"}
```

> A JWKS é buscada ao Keycloak na primeira validação e fica em cache (`_jwks_cache` em `app/auth.py`). Se o Keycloak for reiniciado, fazer `docker compose restart app` para refrescar a cache.

---

## 2. Autorização RBAC

O controlo de acesso usa `require_role()` como FastAPI dependency. O role vem do claim `realm_access.roles` — a API nunca consulta o Keycloak por pedido.

**Regra:** HTTP 401 = sem token válido · HTTP 403 = token válido mas role insuficiente.

### Matriz de acesso

| Endpoint | anónimo | visitante | colaborador | admin |
|---|:---:|:---:|:---:|:---:|
| `/public`, `/health` | ✅ | ✅ | ✅ | ✅ |
| `/me` | ❌ 401 | ✅ | ✅ | ✅ |
| `/colaborador/data`, `/colaborador/perfil` | ❌ 401 | ❌ 403 | ✅ | ✅ |
| `/admin/users`, `/admin/audit` | ❌ 401 | ❌ 403 | ❌ 403 | ✅ |
| `/admin/mfa-area` | ❌ 401 | ❌ 403 | ❌ 403 | ✅ + MFA |

### Verificar RBAC

```bash
# Área colaborador
curl -s -H "Authorization: Bearer $TOKEN_COLAB" http://localhost:8000/colaborador/data  # 200
curl -s -H "Authorization: Bearer $TOKEN_VISIT" http://localhost:8000/colaborador/data  # 403
curl -s -H "Authorization: Bearer $TOKEN_ADMIN" http://localhost:8000/colaborador/data  # 200 (admin inclui colaborador)

# Área admin
curl -s -H "Authorization: Bearer $TOKEN_ADMIN" http://localhost:8000/admin/users | python3 -m json.tool  # 200
curl -s -H "Authorization: Bearer $TOKEN_COLAB" http://localhost:8000/admin/users  # 403
```

---

## 3. MFA / TOTP

`/admin/mfa-area` exige `role: admin` **e** prova de MFA no claim `amr`/`acr` do JWT.

### Configurar TOTP para admin.user

O `admin.user` tem `CONFIGURE_TOTP` como Required Action. No primeiro login via browser:

1. Abrir `http://localhost:8081/realms/iam-tp/account`
2. Fazer login com `admin.user` / `Admin@1234`
3. Seguir o assistente de configuração OTP (Google Authenticator, Authy, etc.)

Para adicionar MFA a outro utilizador:
```text
Keycloak → iam-tp → Users → [utilizador] → Required Actions → Configure OTP
```

### Testar o endpoint protegido por MFA

```bash
# Token obtido via password direto (sem MFA comprovada) → 403
curl -s -H "Authorization: Bearer $TOKEN_ADMIN" http://localhost:8000/admin/mfa-area
# → {"detail":"MFA não verificada. Este endpoint exige autenticação de dois fatores."}

# Para obter token COM MFA:
# 1. Login via browser com admin.user + TOTP
# 2. Usar Authorization Code para obter token com claim "amr": ["otp"]
# 3. Esse token passa no check require_mfa()
```

> `require_mfa()` em `app/auth.py` inspeciona o claim `amr` em busca de `otp`, `mfa`, `2fa` ou `google_authenticator`. O Keycloak apenas emite o claim — a verificação é inteiramente da API.

---

## 4. Ciclo de Vida JML

Os scripts interagem com a Admin REST API do Keycloak. Podem ser executados como **CLI Python** ou via **endpoints REST** (`/admin/jml/*`).

### Configurar ambiente local

```bash
cd jml
pip install -r requirements.txt
```

Criar `jml/.env`:
```ini
KEYCLOAK_URL=http://localhost:8081
KEYCLOAK_REALM=iam-tp
KEYCLOAK_ADMIN=admin
KEYCLOAK_ADMIN_PASSWORD=Admin123!
OIDC_CLIENT_ID=fastapi-client
OIDC_CLIENT_SECRET=Admin123!
```

### Joiner — criar utilizador

```bash
python joiner.py --username alice --email alice@empresa.pt --role colaborador
# → Utilizador 'alice' criado com role 'colaborador' e grupo 'Colaboradores'
```

### Mover — alterar role

```bash
python mover.py --username alice --old-role colaborador --new-role admin
# → Role alterada. Sessões revogadas. Acesso atualizado imediatamente.
```

O Mover revoga sessões via `DELETE /admin/realms/iam-tp/users/{id}/sessions` — sem esperar pela expiração do token (default 300 s).

### Leaver — desativar utilizador

```bash
python leaver.py --username alice
# → Conta desativada, roles removidas, sessões revogadas.

# Verificar que o login falha:
curl -s -X POST http://localhost:8081/realms/iam-tp/protocol/openid-connect/token \
  -d "grant_type=password" -d "client_id=fastapi-client" -d "client_secret=Admin123!" \
  -d "username=alice" -d "password=ChangeMe123!" | python3 -m json.tool
# → {"error": "invalid_grant", "error_description": "Account disabled"}
```

> O Leaver não apaga o utilizador — desativa e remove roles; o histórico de auditoria fica preservado.

### JML via API REST

```bash
# Joiner
curl -s -X POST http://localhost:8000/admin/jml/joiner \
  -H "Authorization: Bearer $TOKEN_ADMIN" -H "Content-Type: application/json" \
  -d '{"username":"carlos","email":"carlos@empresa.pt","role":"visitante"}' | python3 -m json.tool

# Mover
curl -s -X POST http://localhost:8000/admin/jml/mover \
  -H "Authorization: Bearer $TOKEN_ADMIN" -H "Content-Type: application/json" \
  -d '{"username":"carlos","old_role":"visitante","new_role":"colaborador"}' | python3 -m json.tool

# Leaver
curl -s -X POST http://localhost:8000/admin/jml/leaver \
  -H "Authorization: Bearer $TOKEN_ADMIN" -H "Content-Type: application/json" \
  -d '{"username":"carlos"}' | python3 -m json.tool
```

---

## 5. Auditoria

O Keycloak regista eventos de autenticação e administração no PostgreSQL — persistem após restart.

```bash
# Todos os eventos
curl -s -H "Authorization: Bearer $TOKEN_ADMIN" \
  http://localhost:8000/admin/audit | python3 -m json.tool

# Filtrar por tipo
curl -s -H "Authorization: Bearer $TOKEN_ADMIN" \
  "http://localhost:8000/admin/audit?event_type=LOGIN" | python3 -m json.tool

curl -s -H "Authorization: Bearer $TOKEN_ADMIN" \
  "http://localhost:8000/admin/audit?event_type=LOGIN_ERROR" | python3 -m json.tool

# Resumo agregado
curl -s -H "Authorization: Bearer $TOKEN_ADMIN" \
  http://localhost:8000/admin/audit/summary | python3 -m json.tool
```

Saída esperada do resumo:

```json
{
  "LOGIN": 12,
  "LOGOUT": 5,
  "LOGIN_ERROR": 2,
  "UPDATE_PASSWORD": 1
}
```

> Para visualizar no Admin Console: `http://localhost:8081` → `iam-tp` → **Events**

---

## Testes Automatizados

Os testes não requerem serviços em execução — o JWKS é mockado com `unittest.mock.patch.object`.

```bash
pip install -r tests/requirements.txt
python -m pytest tests/ -v
```

| Teste | O que valida |
|---|---|
| `test_get_current_user_decodes_rs256_token` | Decodificação de JWT RS256 com assinatura, issuer e audience |
| `test_require_role_allows_admin` | `require_role("admin")` aceita token com role admin |
| `test_require_role_denies_non_admin` | `require_role("admin")` rejeita token sem role admin (HTTP 403) |
| `test_require_mfa_denies_without_otp` | `require_mfa()` rejeita token sem claim MFA (HTTP 403) |

Resultado esperado: **`4 passed`**

---

## Referência de Endpoints

| Endpoint | Método | Role necessária |
|---|---|---|
| `/health`, `/public`, `/dashboard`, `/auth/token` | GET/POST | — |
| `/me` | GET | qualquer token válido |
| `/colaborador/data`, `/colaborador/perfil` | GET | colaborador, admin |
| `/admin/users`, `/admin/audit`, `/admin/audit/summary` | GET | admin |
| `/admin/mfa-area` | GET | admin + MFA |
| `/admin/jml/joiner`, `/admin/jml/mover`, `/admin/jml/leaver` | POST | admin |

---

## Resolução de Problemas

| Problema | Solução |
|---|---|
| Keycloak não arranca | `docker compose down -v && docker compose up --build` |
| TOTP inválido | Verificar sincronização de hora; aguardar novo código (30 s) |
| Token expirado na demo | Clicar Logout e fazer novo login no dashboard |
| Dashboard não carrega | `docker compose ps` — se `app` não estiver healthy: `docker compose restart app` |
| JWKS desatualizado (keys rotated) | `docker compose restart app` |
| Eventos de auditoria vazios | Fazer logout/login com os 3 utilizadores para gerar eventos |

---

## Checklist Final

- [ ] `docker compose up --build` arranca sem erros
- [ ] `http://localhost:8000/dashboard` abre com CSS
- [ ] `http://localhost:8081` abre o Keycloak Admin Console
- [ ] Tokens obtidos para `colaborador.user`, `admin.user`, `visitante.user`
- [ ] RBAC: 200/403 coerentes conforme a matriz de acesso
- [ ] MFA: `/admin/mfa-area` retorna 403 sem MFA, 200 com MFA
- [ ] JML: Joiner cria · Mover altera role e revoga sessões · Leaver desativa
- [ ] Auditoria: eventos visíveis em `/admin/audit/summary`
- [ ] `python -m pytest tests/ -v` → `4 passed`
