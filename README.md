# IAM TP — Gestão de Identidade

Trabalho Prático da UC de Gestão de Identidade — MEI, ESTG-IPP  
**Stack:** Keycloak 26 · PostgreSQL 16 · Python 3.12 · FastAPI

---

## Pré-requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (inclui Docker Compose v2)
- Python 3.12+ (apenas para scripts JML locais)

---

## Arranque rápido

### 1. Configurar variáveis de ambiente

```bash
cp .env.example .env
# Editar .env com passwords seguras
```

> **Importante:** O valor de `OIDC_CLIENT_SECRET` deve coincidir com o campo `"secret"` do cliente `fastapi-client` no ficheiro `realm-export.json`.

### 2. Iniciar todos os serviços

```bash
docker compose up --build
```

O `docker compose up` inicia automaticamente:
- **PostgreSQL** na porta `5432`
- **Keycloak** na porta `8080` (importa o realm `iam-tp` via `realm-export.json`)
- **FastAPI** na porta `8000`

Aguardar até ao Keycloak estar saudável (pode demorar ~60 segundos na primeira vez).

### 3. Verificar

- Keycloak Admin Console: http://localhost:8080 (credenciais do `.env`)
- FastAPI Swagger UI: http://localhost:8000/docs
- Endpoint de saúde: http://localhost:8000/health

---

## Utilizadores de teste

| Username | Password | Role |
|---|---|---|
| `admin.user` | `Admin@1234` | admin |
| `colaborador.user` | `Colab@1234` | colaborador |
| `visitante.user` | `Visit@1234` | visitante |

> O `admin.user` tem a Required Action `CONFIGURE_TOTP` — será pedido para configurar MFA no primeiro login.

---

## Obter um token de acesso (para testar a API)

### Via Keycloak (Resource Owner Password — apenas para testes)

```bash
TOKEN=$(curl -s -X POST http://localhost:8080/realms/iam-tp/protocol/openid-connect/token \
  -d "grant_type=password" \
  -d "client_id=fastapi-client" \
  -d "client_secret=<OIDC_CLIENT_SECRET>" \
  -d "username=colaborador.user" \
  -d "password=Colab@1234" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

### Testar endpoints

```bash
# Público — sem autenticação
curl http://localhost:8000/public

# Utilizador autenticado — retorna claims
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/me

# Área de colaboradores (role: colaborador ou admin)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/colaborador/data

# Área admin — com token de colaborador → 403 Forbidden
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/admin/users

# Área admin — com token de admin
TOKEN_ADMIN=$(curl -s -X POST http://localhost:8080/realms/iam-tp/protocol/openid-connect/token \
  -d "grant_type=password" -d "client_id=fastapi-client" \
  -d "client_secret=<OIDC_CLIENT_SECRET>" \
  -d "username=admin.user" -d "password=Admin@1234" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -H "Authorization: Bearer $TOKEN_ADMIN" http://localhost:8000/admin/users
curl -H "Authorization: Bearer $TOKEN_ADMIN" http://localhost:8000/admin/audit
curl -H "Authorization: Bearer $TOKEN_ADMIN" http://localhost:8000/admin/audit/summary
```

---

## Scripts JML

Instalar dependências uma vez:

```bash
cd jml
pip install -r requirements.txt
```

Criar um ficheiro `.env` em `jml/` (ou usar o da raiz do projeto):

```bash
# jml/.env
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=iam-tp
KEYCLOAK_ADMIN=admin
KEYCLOAK_ADMIN_PASSWORD=<password do .env>
OIDC_CLIENT_ID=fastapi-client
OIDC_CLIENT_SECRET=<secret do .env>
```

### Joiner — criar novo utilizador

```bash
python joiner.py --username alice --email alice@empresa.pt --role colaborador
python joiner.py --username bob --email bob@empresa.pt --role admin
```

### Mover — alterar role de utilizador

```bash
python mover.py --username alice --old-role colaborador --new-role admin
```

O script revoga as sessões ativas automaticamente — o acesso à API muda imediatamente.

### Leaver — desativar utilizador

```bash
python leaver.py --username alice
```

Desativa a conta, remove todas as roles e revoga sessões. Login passa a falhar.

---

## MFA (TOTP)

O utilizador `admin.user` tem `CONFIGURE_TOTP` como Required Action.  
No primeiro login via Keycloak (http://localhost:8080), será redirecionado para configurar MFA.

Para forçar MFA noutro utilizador via Admin Console:
1. Keycloak → `iam-tp` → Users → selecionar utilizador
2. Credentials → Required Actions → adicionar `Configure OTP`

---

## Auditoria

Eventos são registados automaticamente pelo Keycloak.  
Para consultar via API (requer token de admin):

```bash
# Todos os eventos de utilizador
curl -H "Authorization: Bearer $TOKEN_ADMIN" http://localhost:8000/admin/audit

# Apenas erros de login
curl -H "Authorization: Bearer $TOKEN_ADMIN" "http://localhost:8000/admin/audit?event_type=LOGIN_ERROR"

# Resumo por tipo de evento
curl -H "Authorization: Bearer $TOKEN_ADMIN" http://localhost:8000/admin/audit/summary
```

---

## Reprodutibilidade

O ficheiro `realm-export.json` é importado automaticamente no arranque.  
Para re-exportar o realm após alterações:

```bash
docker exec -it <keycloak-container-id> \
  /opt/keycloak/bin/kc.sh export --realm iam-tp --file /tmp/realm-export.json

docker cp <keycloak-container-id>:/tmp/realm-export.json ./realm-export.json
```

---

## Estrutura do projeto

```
Projeto_IAM/
├── docker-compose.yml
├── .env.example
├── realm-export.json        # Configuração Keycloak (versionado)
├── app/                     # FastAPI
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── auth.py              # Validação JWT + RBAC
│   ├── config.py
│   └── routes/
│       ├── public.py        # /health, /public, /me
│       ├── colaborador.py   # /colaborador/* (role: colaborador, admin)
│       └── admin.py         # /admin/* (role: admin)
└── jml/                     # Scripts JML
    ├── requirements.txt
    ├── _keycloak_client.py  # Cliente Admin API partilhado
    ├── joiner.py
    ├── mover.py
    └── leaver.py
```
