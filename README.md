# IAM TP — Gestão de Identidade e Acesso

**UC:** Gestão de Identidade · MEI, ESTG-IPP · 2025/2026  
**Stack:** Keycloak 26 · PostgreSQL 16 · Python 3.12 · FastAPI

Este projeto implementa uma plataforma de **Identity and Access Management (IAM)** containerizada que demonstra autenticação OIDC/OAuth2, controlo de acesso baseado em papéis (RBAC), autenticação multifator (MFA/TOTP), ciclo de vida de utilizadores (JML) e auditoria de eventos — todos integrados através do Keycloak como Identity Provider.

---

## Arquitetura

```text
┌─────────────────────────────── Docker Compose ───────────────────────────────┐
│                                                                               │
│   ┌─────────────────────┐   OIDC / JWT   ┌───────────────────────────────┐  │
│   │      FastAPI         │◄──────────────►│          Keycloak 26          │  │
│   │      :8000           │                │          :8080 (interno)      │  │
│   │                      │                │          :8081 (externo)      │  │
│   │  /public  (sem auth) │                │                               │  │
│   │  /me      (token)    │                │  Realm: iam-tp                │  │
│   │  /colaborador (RBAC) │                │  Roles: admin, colaborador,   │  │
│   │  /admin   (RBAC+MFA) │                │         visitante             │  │
│   │  /admin/audit        │                │  MFA: TOTP obrigatório(admin) │  │
│   └─────────────────────┘                └───────────────┬───────────────┘  │
│                                                           │                   │
│   ┌──────────────────────────────────────┐               │                   │
│   │  JML Scripts (Python CLI)            │  Admin API    │                   │
│   │  joiner.py · mover.py · leaver.py   │──────────────►│                   │
│   └──────────────────────────────────────┘               │                   │
│                                                           ▼                   │
│                                          ┌───────────────────────────────┐   │
│                                          │       PostgreSQL 16            │   │
│                                          │    (base de dados Keycloak)   │   │
│                                          └───────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────────────────┘
```

**Fluxo de autenticação:**

1. Cliente autentica no Keycloak → recebe JWT assinado (RS256)
2. JWT contém roles em `realm_access.roles`
3. FastAPI valida assinatura via JWKS, extrai roles, aplica RBAC
4. `require_role()` / `require_mfa()` protegem os endpoints

---

## Pré-requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (inclui Docker Compose v2)
- Python 3.12+ (apenas para scripts JML e testes locais)

---

## Fase 1 — Arranque da Infraestrutura

### 1.1 Configurar variáveis de ambiente

Criar o ficheiro `.env` na raiz do projeto:

```ini
KEYCLOAK_ADMIN=admin
KEYCLOAK_ADMIN_PASSWORD=Admin123!
DB_PASSWORD=Admin123!
OIDC_CLIENT_ID=fastapi-client
OIDC_CLIENT_SECRET=Admin123!
```

> O valor de `OIDC_CLIENT_SECRET` deve coincidir com o campo `"secret"` do cliente `fastapi-client` em `realm-export.json`.

### 1.2 Iniciar todos os serviços

```bash
docker compose up --build
```

O arranque completo demora **2–3 minutos** na primeira vez (Keycloak tem 90 s de startup antes de aceitar ligações). Aguardar até ver nos logs:

```text
keycloak  | Listening on: http://0.0.0.0:8080
app       | Application startup complete.
```

### 1.3 Verificar serviços

```bash
# Keycloak Admin Console
open http://localhost:8081

# FastAPI — Swagger UI interativo
open http://localhost:8000/docs

# FastAPI — Dashboard de demonstração
open http://localhost:8000/dashboard

# Health check da API
curl http://localhost:8000/health
# → {"status":"ok"}

# Endpoint público (sem autenticação)
curl http://localhost:8000/public
# → {"message":"Este é um recurso público. Não requer autenticação."}
```

---

## Utilizadores de Teste

| Username | Password | Role | Notas |
| --- | --- | --- | --- |
| `admin.user` | `Admin@1234` | admin | MFA (TOTP) obrigatório no 1.º login |
| `colaborador.user` | `Colab@1234` | colaborador | — |
| `visitante.user` | `Visit@1234` | visitante | — |

---

## Fase 2 — Autenticação OIDC e Validação JWT

### 2.1 Obter token de acesso

```bash
# Token para colaborador
TOKEN=$(curl -s -X POST http://localhost:8081/realms/iam-tp/protocol/openid-connect/token \
  -d "grant_type=password" \
  -d "client_id=fastapi-client" \
  -d "client_secret=Admin123!" \
  -d "username=colaborador.user" \
  -d "password=Colab@1234" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo "Token obtido: ${TOKEN:0:60}..."
```

> Este fluxo `password` é usado como atalho de teste. O cliente `fastapi-client` suporta também Authorization Code + PKCE (`standardFlowEnabled: true`, `pkce.code.challenge.method: S256`), que é o fluxo recomendado para aplicações browser.

### 2.2 Inspecionar o JWT (opcional)

```bash
# Ver claims do token sem validação de assinatura
echo $TOKEN | python3 -c "
import sys, base64, json
token = sys.stdin.read().strip()
payload = token.split('.')[1]
payload += '=' * (4 - len(payload) % 4)
print(json.dumps(json.loads(base64.urlsafe_b64decode(payload)), indent=2))
"
```

Saída esperada (resumida):

```json
{
  "iss": "http://keycloak:8080/realms/iam-tp",
  "sub": "...",
  "preferred_username": "colaborador.user",
  "realm_access": {
    "roles": ["colaborador", "default-roles-iam-tp"]
  }
}
```

### 2.3 Verificar identidade do utilizador autenticado

```bash
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/me | python3 -m json.tool
```

Saída esperada:

```json
{
  "sub": "...",
  "preferred_username": "colaborador.user",
  "email": "colaborador@empresa.pt",
  "roles": ["colaborador"]
}
```

### 2.4 Token inválido deve ser rejeitado

```bash
curl -s -H "Authorization: Bearer token_invalido" http://localhost:8000/me
# → {"detail":"Token inválido"}  (HTTP 401)

curl -s http://localhost:8000/me
# → {"detail":"Not authenticated"}  (HTTP 401)
```

---

## Fase 3 — Controlo de Acesso Baseado em Papéis (RBAC)

### 3.1 Obter tokens para cada role

```bash
# Token colaborador (já obtido acima)
TOKEN_COLAB=$TOKEN

# Token admin
TOKEN_ADMIN=$(curl -s -X POST http://localhost:8081/realms/iam-tp/protocol/openid-connect/token \
  -d "grant_type=password" \
  -d "client_id=fastapi-client" \
  -d "client_secret=Admin123!" \
  -d "username=admin.user" \
  -d "password=Admin@1234" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Token visitante
TOKEN_VISIT=$(curl -s -X POST http://localhost:8081/realms/iam-tp/protocol/openid-connect/token \
  -d "grant_type=password" \
  -d "client_id=fastapi-client" \
  -d "client_secret=Admin123!" \
  -d "username=visitante.user" \
  -d "password=Visit@1234" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

### 3.2 Área de colaboradores

```bash
# colaborador → 200 OK
curl -s -H "Authorization: Bearer $TOKEN_COLAB" http://localhost:8000/colaborador/data
# → {"documentos": [...]}

curl -s -H "Authorization: Bearer $TOKEN_COLAB" http://localhost:8000/colaborador/perfil
# → {"username": "colaborador.user", "role": "colaborador", ...}

# admin também tem acesso → 200 OK
curl -s -H "Authorization: Bearer $TOKEN_ADMIN" http://localhost:8000/colaborador/data
# → 200 OK

# visitante NÃO tem acesso → 403 Forbidden
curl -s -H "Authorization: Bearer $TOKEN_VISIT" http://localhost:8000/colaborador/data
# → {"detail":"Acesso negado. Role necessária: colaborador"}

# sem token → 401 Unauthorized
curl -s http://localhost:8000/colaborador/data
# → {"detail":"Not authenticated"}
```

### 3.3 Área de administração

```bash
# admin → 200 OK — lista de utilizadores do Keycloak
curl -s -H "Authorization: Bearer $TOKEN_ADMIN" http://localhost:8000/admin/users | python3 -m json.tool

# colaborador NÃO tem acesso → 403 Forbidden
curl -s -H "Authorization: Bearer $TOKEN_COLAB" http://localhost:8000/admin/users
# → {"detail":"Acesso negado. Role necessária: admin"}

# visitante NÃO tem acesso → 403 Forbidden
curl -s -H "Authorization: Bearer $TOKEN_VISIT" http://localhost:8000/admin/users
# → {"detail":"Acesso negado. Role necessária: admin"}
```

---

## Fase 4 — Autenticação Multifator (MFA / TOTP)

### 4.1 Configurar TOTP para admin.user

O `admin.user` tem `CONFIGURE_TOTP` como Required Action. No primeiro login no Keycloak ([http://localhost:8081](http://localhost:8081)) será pedido para configurar MFA:

1. Abrir `http://localhost:8081/realms/iam-tp/account`
2. Fazer login com `admin.user` / `Admin@1234`
3. Seguir o assistente de configuração de OTP (usar Google Authenticator, Authy, etc.)

Para adicionar MFA a outro utilizador via Admin Console:

```text
Keycloak → iam-tp → Users → [utilizador] → Required Actions → Configure OTP
```

### 4.2 Endpoint protegido por MFA

O endpoint `/admin/mfa-area` exige `role: admin` **e** prova de MFA no JWT (`amr`/`acr`).

```bash
# Token admin obtido SEM MFA (fluxo password direto) → 403 Forbidden
curl -s -H "Authorization: Bearer $TOKEN_ADMIN" http://localhost:8000/admin/mfa-area
# → {"detail":"MFA não verificada. Este endpoint exige autenticação de dois fatores."}

# Para obter token com MFA comprovada:
# 1. Fazer login via browser em http://localhost:8081 com admin.user + TOTP
# 2. Usar o fluxo Authorization Code para obter um token que inclui "otp" no claim "amr"
# 3. Esse token passa no check require_mfa()
```

> O `require_mfa()` em `app/auth.py` inspeciona o claim `amr` (Authentication Methods Reference) em busca de `otp`, `mfa`, `2fa` ou `google_authenticator`. Tokens emitidos via fluxo password direto sem TOTP não passam neste check.

### 4.3 Verificar MFA nos logs de auditoria

```bash
curl -s -H "Authorization: Bearer $TOKEN_ADMIN" \
  "http://localhost:8000/admin/audit?event_type=LOGIN" | python3 -m json.tool
```

---

## Fase 5 — Ciclo de Vida de Utilizadores (JML)

Os scripts JML interagem com a **Admin REST API do Keycloak**. Podem ser executados localmente (CLI) ou via endpoints da FastAPI (`/admin/jml/*`).

### 5.1 Configurar ambiente local

```bash
cd jml
pip install -r requirements.txt

# Criar jml/.env
cat > .env << 'EOF'
KEYCLOAK_URL=http://localhost:8081
KEYCLOAK_REALM=iam-tp
KEYCLOAK_ADMIN=admin
KEYCLOAK_ADMIN_PASSWORD=Admin123!
OIDC_CLIENT_ID=fastapi-client
OIDC_CLIENT_SECRET=Admin123!
EOF
```

### 5.2 Joiner — criar novo utilizador

```bash
# Criar utilizador com role colaborador
python joiner.py --username alice --email alice@empresa.pt --role colaborador
# → Utilizador 'alice' criado com role 'colaborador' e grupo 'Colaboradores'

# Criar utilizador com role admin
python joiner.py --username bob --email bob@empresa.pt --role admin
# → Utilizador 'bob' criado com role 'admin' e grupo 'Admins'
```

Verificar na API:

```bash
# alice obtém token e acede à área de colaboradores
TOKEN_ALICE=$(curl -s -X POST http://localhost:8081/realms/iam-tp/protocol/openid-connect/token \
  -d "grant_type=password" \
  -d "client_id=fastapi-client" \
  -d "client_secret=Admin123!" \
  -d "username=alice" \
  -d "password=ChangeMe123!" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s -H "Authorization: Bearer $TOKEN_ALICE" http://localhost:8000/colaborador/data
# → 200 OK

curl -s -H "Authorization: Bearer $TOKEN_ALICE" http://localhost:8000/admin/users
# → 403 Forbidden (alice é colaborador, não admin)
```

### 5.3 Mover — alterar role de utilizador

```bash
# Promover alice de colaborador para admin
python mover.py --username alice --old-role colaborador --new-role admin
# → Role alterada. Sessões revogadas. Acesso atualizado imediatamente.
```

Verificar que o acesso muda **imediatamente** (sessões são revogadas):

```bash
# Token antigo de alice (role: colaborador) já não funciona
curl -s -H "Authorization: Bearer $TOKEN_ALICE" http://localhost:8000/colaborador/data
# → 401 Unauthorized (sessão revogada)

# Novo token com role admin
TOKEN_ALICE=$(curl -s -X POST http://localhost:8081/realms/iam-tp/protocol/openid-connect/token \
  -d "grant_type=password" -d "client_id=fastapi-client" \
  -d "client_secret=Admin123!" -d "username=alice" -d "password=ChangeMe123!" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s -H "Authorization: Bearer $TOKEN_ALICE" http://localhost:8000/admin/users
# → 200 OK (alice agora é admin)
```

### 5.4 Leaver — desativar utilizador

```bash
# Desativar alice (saída da organização)
python leaver.py --username alice
# → Conta desativada, roles removidas, sessões revogadas.
```

Verificar que o login falha:

```bash
curl -s -X POST http://localhost:8081/realms/iam-tp/protocol/openid-connect/token \
  -d "grant_type=password" -d "client_id=fastapi-client" \
  -d "client_secret=Admin123!" -d "username=alice" -d "password=ChangeMe123!" \
  | python3 -m json.tool
# → {"error": "invalid_grant", "error_description": "Account disabled"}
```

### 5.5 JML via API (equivalente ao CLI)

Os mesmos fluxos JML estão disponíveis como endpoints REST (requerem token de admin):

```bash
# Joiner via API
curl -s -X POST http://localhost:8000/admin/jml/joiner \
  -H "Authorization: Bearer $TOKEN_ADMIN" \
  -H "Content-Type: application/json" \
  -d '{"username":"carlos","email":"carlos@empresa.pt","role":"visitante"}' \
  | python3 -m json.tool

# Mover via API
curl -s -X POST http://localhost:8000/admin/jml/mover \
  -H "Authorization: Bearer $TOKEN_ADMIN" \
  -H "Content-Type: application/json" \
  -d '{"username":"carlos","old_role":"visitante","new_role":"colaborador"}' \
  | python3 -m json.tool

# Leaver via API
curl -s -X POST http://localhost:8000/admin/jml/leaver \
  -H "Authorization: Bearer $TOKEN_ADMIN" \
  -H "Content-Type: application/json" \
  -d '{"username":"carlos"}' \
  | python3 -m json.tool
```

---

## Fase 6 — Auditoria e Monitorização

O Keycloak regista automaticamente eventos de autenticação e administração.

```bash
# Todos os eventos de utilizador (requer token admin)
curl -s -H "Authorization: Bearer $TOKEN_ADMIN" \
  http://localhost:8000/admin/audit | python3 -m json.tool

# Filtrar por tipo de evento
curl -s -H "Authorization: Bearer $TOKEN_ADMIN" \
  "http://localhost:8000/admin/audit?event_type=LOGIN" | python3 -m json.tool

curl -s -H "Authorization: Bearer $TOKEN_ADMIN" \
  "http://localhost:8000/admin/audit?event_type=LOGIN_ERROR" | python3 -m json.tool

# Resumo agregado por tipo de evento
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

> Para visualizar eventos no Admin Console: `http://localhost:8081` → `iam-tp` → Events

---

## Testes Automatizados

```bash
# Instalar dependências
pip install -r requirements-dev.txt -r app/requirements.txt

# Executar todos os testes (não requer serviços em execução — JWKS é mockado)
python -m pytest tests/ -v
```

Os testes em [tests/test_auth.py](tests/test_auth.py) cobrem:

| Teste | O que valida |
| --- | --- |
| `test_get_current_user_decodes_rs256_token` | Decodificação de JWT RS256 com verificação de assinatura, issuer e audience |
| `test_require_role_allows_admin` | `require_role("admin")` aceita token com role admin |
| `test_require_role_denies_non_admin` | `require_role("admin")` rejeita token sem role admin (HTTP 403) |
| `test_require_mfa_denies_without_otp` | `require_mfa()` rejeita token sem claim MFA (HTTP 403) |

Executar um teste individual:

```bash
python -m pytest tests/test_auth.py::test_require_role_allows_admin -v
```

---

## Reprodutibilidade — Re-exportar Realm

Após alterar a configuração no Keycloak Admin Console, exportar para versionar:

```bash
docker exec -it $(docker compose ps -q keycloak) \
  /opt/keycloak/bin/kc.sh export --realm iam-tp --file /tmp/realm-export.json

docker cp $(docker compose ps -q keycloak):/tmp/realm-export.json ./realm-export.json
```

O ficheiro `realm-export.json` é importado automaticamente em cada `docker compose up`, garantindo reprodutibilidade do ambiente.

---

## Referência de Endpoints

| Endpoint | Método | Auth | Role |
| --- | --- | --- | --- |
| `/health` | GET | — | — |
| `/public` | GET | — | — |
| `/dashboard` | GET | — | — |
| `/auth/token` | POST | — | — |
| `/me` | GET | JWT | qualquer |
| `/colaborador/data` | GET | JWT | colaborador, admin |
| `/colaborador/perfil` | GET | JWT | colaborador, admin |
| `/admin/users` | GET | JWT | admin |
| `/admin/audit` | GET | JWT | admin |
| `/admin/audit/summary` | GET | JWT | admin |
| `/admin/mfa-area` | GET | JWT | admin + MFA |
| `/admin/jml/joiner` | POST | JWT | admin |
| `/admin/jml/mover` | POST | JWT | admin |
| `/admin/jml/leaver` | POST | JWT | admin |

---

## Estrutura do Projeto

```text
Projeto_IAM/
├── docker-compose.yml
├── realm-export.json          # Configuração Keycloak (versionado)
├── app/                       # FastAPI
│   ├── Dockerfile
│   ├── main.py                # Registo de routers e CORS
│   ├── config.py              # Pydantic Settings — URLs derivadas de KEYCLOAK_URL
│   ├── auth.py                # Validação JWT (RS256) + require_role() + require_mfa()
│   ├── keycloak_client.py     # Helpers async para Admin API (uso interno Docker)
│   ├── routes/
│   │   ├── public.py          # /health, /public, /me, /auth/token, /dashboard
│   │   ├── colaborador.py     # /colaborador/*
│   │   └── admin.py          # /admin/* + JML endpoints
│   └── static/
│       └── dashboard.html     # SPA de demonstração
├── jml/                       # Scripts de ciclo de vida (Python CLI)
│   ├── _keycloak_client.py    # Cliente Admin API (síncrono, uso local)
│   ├── joiner.py
│   ├── mover.py
│   └── leaver.py
└── tests/
    └── test_auth.py           # Testes JWT/RBAC (sem serviços em execução)
```
