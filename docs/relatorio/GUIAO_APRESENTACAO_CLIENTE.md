# Guião de Teste e Apresentação ao Cliente

Este documento serve como roteiro para validar e demonstrar o projeto IAM do TP de Gestão de Identidade, com base no enunciado `docs/ESTG-IPP-MEI-GI-trabalho-pratico2526.pdf`.

## 1. Estado de Conformidade com o Enunciado

| Requisito do cliente / enunciado | Estado | Evidência no projeto | Como demonstrar |
|---|---:|---|---|
| Keycloak como componente central IAM / IdP / SSO | Cumprido | `docker-compose.yml`, `realm-export.json` | `docker compose up -d`; abrir `http://localhost:8081` |
| Realm dedicado ao TP | Cumprido | `realm-export.json`, realm `iam-tp` | Keycloak Admin Console ou tab Arquitetura |
| Diretório de identidades no Keycloak | Cumprido | Utilizadores, grupos e roles em `realm-export.json` | Dashboard tab Autenticação/JML ou Keycloak |
| Pelo menos 3 perfis | Cumprido | `admin`, `colaborador`, `visitante` | Dashboard tab Relatório/Autorização |
| Cliente OIDC integrado numa aplicação | Cumprido | Cliente `fastapi-client` em `realm-export.json`; `/auth/token` em `app/routes/public.py` | Login no dashboard |
| Validação de sessão/token e claims | Cumprido | `app/auth.py`, `/me` | Login e consultar payload/claims no dashboard |
| Autorização por papéis/políticas | Cumprido | `require_role()` em `app/auth.py`; rotas `colaborador` e `admin` | Tab Autorização, botão `Testar Todos` |
| Prova de permitir/negar recursos | Cumprido | `/public`, `/me`, `/colaborador/*`, `/admin/*` | Testar com colaborador, visitante e admin |
| MFA TOTP via Keycloak | Cumprido | `CONFIGURE_TOTP`, `browser-mfa`, `auth-otp-form` em `realm-export.json`; `require_mfa()` | Login browser em Keycloak e endpoint `/admin/mfa-area` |
| Zona protegida exige MFA | Cumprido | `/admin/mfa-area` em `app/routes/admin.py` | Token admin sem MFA retorna 403; token com MFA retorna 200 |
| Joiner integrado com Keycloak | Cumprido | `jml/joiner.py`; `/admin/jml/joiner` | Criar `demo.user` na tab JML |
| Mover integrado com Keycloak | Cumprido | `jml/mover.py`; `/admin/jml/mover` | Mudar `demo.user` de colaborador para admin |
| Leaver integrado com Keycloak | Cumprido | `jml/leaver.py`; `/admin/jml/leaver` | Desativar `demo.user` e confirmar login bloqueado |
| Revogação/impacto imediato de sessões | Cumprido | `DELETE /users/{id}/sessions` em mover/leaver | Fazer mover/leaver e pedir novo login/token |
| Auditoria de eventos críticos | Cumprido | Eventos e admin events em `realm-export.json`; `/admin/audit` | Tab Auditoria, filtros LOGIN/LOGIN_ERROR |
| Evidência consultável | Cumprido | Dashboard tab Auditoria; endpoints `/admin/audit*` | Mostrar eventos no dashboard |
| `docker compose up` inicia Keycloak, Postgres e app | Cumprido | `docker-compose.yml` | `docker compose up -d --build` |
| Export/import de realm | Cumprido | `realm-export.json` montado no Keycloak | Remover volumes e subir stack para reproduzir |
| Execução reproduzível | Cumprido | `README.md`, este guião | Seguir secções 2 e 3 |
| Segurança básica sem secrets hardcoded em código | Cumprido com nota | Secrets em `.env` e variáveis Docker; há credenciais de demo no realm/README | Usar apenas credenciais fictícias em demo |
| Organização de código clara | Cumprido | `app/`, `jml/`, `tests/`, `docs/` | Mostrar estrutura do projeto |
| Relatório curto 5-8 páginas | Parcial / a confirmar | Existe `README.md` e tab `Relatório` no dashboard; não foi encontrado ficheiro standalone de relatório | Se o docente exigir PDF/DOCX, exportar a tab Relatório ou criar relatório separado |
| Demo ao vivo 10 minutos | Cumprido | Dashboard e este guião | Seguir secção 3 |

Conclusão: os pontos técnicos obrigatórios estão implementados e testáveis. A única ressalva é o entregável formal “relatório curto 5-8 páginas”, porque não existe um ficheiro separado com esse nome/formato na raiz ou em `docs/`.

## 2. Preparação Antes da Demo

1. Confirmar que o ficheiro `.env` existe na raiz:

```env
KEYCLOAK_ADMIN=admin
KEYCLOAK_ADMIN_PASSWORD=Admin123!
DB_PASSWORD=Admin123!
OIDC_CLIENT_ID=fastapi-client
OIDC_CLIENT_SECRET=Admin123!
```

2. Subir a stack:

```powershell
docker compose up -d --build
```

3. Aguardar 2 a 3 minutos até o Keycloak ficar saudável.

4. Confirmar serviços:

```powershell
docker compose ps
```

5. Validar a API:

```powershell
Invoke-WebRequest http://localhost:8000/health -UseBasicParsing
```

Resultado esperado: `{"status":"ok","service":"IAM TP — FastAPI"}`.

6. Abrir:

```text
http://localhost:8000/dashboard
```

7. Confirmar que o CSS está ativo:

```text
http://localhost:8000/static/dashboard.css
```

Resultado esperado: HTTP 200 com conteúdo CSS.

## 3. Simulação de Apresentação ao Cliente

### 3.1 Abertura e Arquitetura

Objetivo: mostrar que a solução é IAM centralizada com Keycloak.

1. Abrir `http://localhost:8000/dashboard`.
2. Na tab `Relatório`, explicar:
   - Keycloak é o IdP/SSO.
   - FastAPI valida JWT RS256 via JWKS.
   - PostgreSQL guarda a configuração e dados do Keycloak.
   - O realm é reproduzível via `realm-export.json`.
3. Na tab `Arquitetura`, mostrar os componentes e portas:
   - Dashboard/API: `localhost:8000`
   - Keycloak: `localhost:8081`
   - PostgreSQL: interno no Docker

### 3.2 Autenticação OIDC

Objetivo: provar login e claims.

1. Ir à tab `Autenticação`.
2. Escolher preset `colaborador.user`.
3. Clicar `Entrar via Keycloak`.
4. Mostrar:
   - `preferred_username`
   - `email`
   - `sub`
   - `realm_access.roles`
   - expiração do token

Também pode ser testado por terminal:

```powershell
$body = @{
  username = "colaborador.user"
  password = "Colab@1234"
} | ConvertTo-Json

Invoke-WebRequest `
  -Uri http://localhost:8000/auth/token `
  -Method POST `
  -ContentType "application/json" `
  -Body $body `
  -UseBasicParsing
```

Resultado esperado: resposta com `access_token`.

### 3.3 Autorização RBAC

Objetivo: provar permitir/negar por role.

1. Com sessão `colaborador.user`, ir à tab `Autorização`.
2. Clicar `Testar Todos`.
3. Confirmar resultados esperados:
   - `/public`: 200
   - `/me`: 200
   - `/colaborador/data`: 200
   - `/colaborador/perfil`: 200
   - `/admin/users`: 403
   - `/admin/audit`: 403
   - `/admin/mfa-area`: 403
4. Fazer logout.
5. Repetir com `visitante.user`.
6. Confirmar que visitante só consegue recursos públicos e `/me`, mas não recursos de colaborador/admin.

### 3.4 Administração com Admin

Objetivo: mostrar acesso privilegiado.

1. Fazer login como `admin.user` / `Admin@1234`.
2. Se o Keycloak pedir TOTP, usar a aplicação Authenticator configurada.
3. Na tab `Autorização`, clicar `Testar Todos`.
4. Confirmar:
   - `/admin/users`: 200
   - `/admin/audit`: 200
   - `/admin/mfa-area`: 403 se o token veio do fluxo password sem MFA comprovado; 200 se o token tiver claim MFA.

### 3.5 MFA TOTP

Objetivo: provar segunda camada de autenticação.

1. Abrir:

```text
http://localhost:8081/realms/iam-tp/account
```

2. Entrar com:

```text
admin.user / Admin@1234
```

3. Se for o primeiro login, configurar TOTP:
   - Ler QR Code com Google Authenticator, Microsoft Authenticator, Authy ou equivalente.
   - Inserir o OTP de 6 dígitos.
4. Obter ou colar token com MFA na área `Token externo (MFA demo)` da tab `Autenticação`.
5. Testar `/admin/mfa-area`.

Resultado esperado:
   - Token admin sem MFA: 403.
   - Token admin com MFA: 200.

### 3.6 JML: Joiner

Objetivo: criar uma identidade no Keycloak.

1. Estar autenticado como admin.
2. Ir à tab `JML`.
3. Em `Joiner`, criar:

```text
Username: demo.user
Email: demo.user@empresa.pt
Role: colaborador
Password: Demo@1234
```

4. Clicar `Criar utilizador no Keycloak`.
5. Confirmar que `demo.user` aparece na lista de utilizadores.
6. Fazer logout e tentar login como `demo.user`.

Nota: o utilizador criado pode ter password temporária e o Keycloak pode pedir alteração no primeiro login.

### 3.7 JML: Mover

Objetivo: mudar role/grupo e provar impacto no acesso.

1. Voltar a entrar como admin.
2. Na tab `JML`, secção `Mover`, usar:

```text
Username: demo.user
Role atual: colaborador
Nova role: admin
```

3. Clicar `Mover + Revogar sessões`.
4. Confirmar que as sessões são revogadas.
5. Fazer novo login com `demo.user`.
6. Testar `/admin/users`.

Resultado esperado: depois de novo login, `demo.user` tem role admin e consegue aceder a recursos admin.

### 3.8 JML: Leaver

Objetivo: desativar identidade e cortar acesso.

1. Na tab `JML`, secção `Leaver`, usar:

```text
Username: demo.user
```

2. Clicar `Desativar + Revogar sessões`.
3. Fazer logout.
4. Tentar login com `demo.user`.

Resultado esperado: login falha porque o utilizador foi desativado, roles removidas e sessões revogadas.

### 3.9 Auditoria

Objetivo: provar evidência consultável de eventos.

1. Entrar como admin.
2. Ir à tab `Auditoria`.
3. Mostrar:
   - Eventos de login.
   - Eventos de erro de login.
   - Eventos administrativos JML.
   - Resumo por tipo.
4. Usar o filtro para `LOGIN`, `LOGIN_ERROR` ou `UPDATE_TOTP`.

Também pode ser testado via endpoint:

```powershell
Invoke-WebRequest `
  -Uri "http://localhost:8000/admin/audit?event_type=LOGIN" `
  -Headers @{ Authorization = "Bearer <TOKEN_ADMIN>" } `
  -UseBasicParsing
```

## 4. Testes Automáticos

Instalar dependências:

```powershell
python -m pip install -r app/requirements.txt -r requirements-dev.txt
```

Correr testes:

```powershell
python -m pytest tests/ -v
```

Resultado validado:

```text
4 passed
```

Os testes cobrem:

| Teste | Cobertura |
|---|---|
| `test_require_role_allows_admin` | Role admin aceite |
| `test_require_role_denies_non_admin` | Role insuficiente rejeitada |
| `test_require_mfa_denies_without_otp` | MFA obrigatório rejeita token sem OTP |
| `test_get_current_user_decodes_rs256_token` | JWT RS256 validado com JWKS, issuer e audience |

## 5. Plano de Demo em 10 Minutos

| Minuto | Ação | Prova |
|---:|---|---|
| 0-1 | Mostrar arquitetura e stack Docker | Dashboard tab Relatório/Arquitetura |
| 1-2 | Login colaborador | Claims e roles no token |
| 2-3 | Testar RBAC colaborador | 200 em colaborador, 403 em admin |
| 3-4 | Login visitante | Acesso mínimo |
| 4-5 | Login admin | Acesso a `/admin/users` |
| 5-6 | Demonstrar MFA | `/admin/mfa-area` exige MFA |
| 6-7 | Joiner | Criar `demo.user` |
| 7-8 | Mover | Mudar role e revogar sessões |
| 8-9 | Leaver | Desativar utilizador |
| 9-10 | Auditoria | Mostrar eventos e resumo |

## 6. Checklist Final Antes de Entregar

- [ ] `docker compose up -d --build` arranca sem erros.
- [ ] `http://localhost:8000/dashboard` abre com CSS.
- [ ] `http://localhost:8081` abre o Keycloak.
- [ ] Login `colaborador.user` funciona.
- [ ] Login `visitante.user` funciona.
- [ ] Login `admin.user` funciona.
- [ ] RBAC mostra 200/403 coerentes.
- [ ] MFA foi configurado pelo menos uma vez para `admin.user`.
- [ ] Joiner cria utilizador no Keycloak.
- [ ] Mover altera role/grupo e revoga sessões.
- [ ] Leaver desativa utilizador e revoga sessões.
- [ ] Auditoria mostra eventos de utilizador e admin.
- [ ] `python -m pytest tests/ -v` passa.
- [ ] Confirmar se o docente exige relatório formal em PDF/DOCX separado.

