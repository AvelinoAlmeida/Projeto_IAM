# DEMO.md — Script de Demonstração (10 minutos)

**Evento:** Trabalho Prático — Gestão de Identidade | MEI-ESTG-IPP  
**Docente:** Ricardo Costa  
**Data:** 28 de maio de 2026  
**URL principal:** `http://localhost:8000/dashboard`  
**Keycloak Admin:** `http://localhost:8081`

---

## Pré-requisitos (antes de entrar na sala)

```bash
docker compose up
```

Aguardar até os 3 serviços estarem healthy (≈ 2–3 min):
- `keycloak` → health check em `:9000/health/ready`
- `postgres` → `pg_isready`
- `app` → FastAPI em `:8000`

Abrir no browser: `http://localhost:8000/dashboard`  
Deixar o terminal visível numa janela secundária.

---

## Credenciais

| Utilizador | Password | Role | Notas |
|---|---|---|---|
| `admin.user` | `Admin@1234` | admin | **TOTP obrigatório** — ter o Google Authenticator pronto |
| `colaborador.user` | `Colab@1234` | colaborador | Acesso a `/colaborador/*` |
| `visitante.user` | `Visit@1234` | visitante | Só `/public` e `/me` |

---

## Bloco 0 — Arranque e Arquitetura · `00:00 – 01:00`

**Frase de abertura:**
> "O sistema arranca inteiro com um único comando — `docker compose up`. Temos três serviços: Keycloak como IdP, PostgreSQL como backend do Keycloak, e uma API FastAPI que valida os JWTs e aplica RBAC."

**Passos:**
1. Mostrar o terminal com os logs dos 3 serviços healthy
2. Abrir `http://localhost:8000/dashboard` → Tab **Home / Relatório**
3. Apontar o diagrama de arquitetura (secção "Arquitetura" ou Tab Arquitetura)
4. Mencionar: realm `iam-tp`, 3 roles, realm-export.json versionado no git

**O que realçar tecnicamente:**
- O Keycloak importa o realm automaticamente no arranque (`--import-realm`)
- O FastAPI só fica ready depois do Keycloak estar healthy (`depends_on` + health check)
- Todos os secrets estão em `.env`, sem nada hardcoded no código

**Transição:** *"Vamos ver a autenticação em ação."*

---

## Bloco 1 — Autenticação OIDC · `01:00 – 03:00`

**Frase de abertura:**
> "A autenticação é feita via OIDC contra o Keycloak. A API valida o JWT com a chave pública RS256 — nunca vê a password."

**Passos:**
1. Tab **Autenticação** no dashboard
2. Selecionar preset **`colaborador.user`** → clicar **Login**
3. Mostrar o JWT decoded: `sub`, `email`, `preferred_username`, `realm_access.roles: ["colaborador"]`, countdown de expiração
4. Clicar **Logout**
5. Selecionar preset **`visitante.user`** → clicar **Login**
6. Comparar: `realm_access.roles: ["visitante"]` — role diferente, mesmo flow

**O que realçar tecnicamente:**
- Endpoint `/auth/token` usa o grant *Resource Owner Password Credentials* (só para testes)
- Em produção o fluxo seria *Authorization Code + PKCE*
- O FastAPI busca a JWKS do Keycloak na primeira validação e faz cache em memória (`_jwks_cache` em `auth.py`)

**Transição:** *"Agora que temos um token, vemos o que cada role pode aceder."*

---

## Bloco 2 — Autorização / RBAC · `03:00 – 04:30`

**Frase de abertura:**
> "Cada endpoint é protegido por um `require_role()` FastAPI dependency. Vamos testar todos ao mesmo tempo."

**Passos:**
1. Manter sessão como `visitante.user` (ou fazer login se expirou)
2. Tab **Autorização** → clicar **Testar Todos os Endpoints**
3. Mostrar a tabela de resultados:
   - `/public` → **200** ✅
   - `/me` → **200** ✅ (token válido)
   - `/colaborador/data` → **403** ❌ (visitante não tem a role)
   - `/admin/users` → **403** ❌
4. Mudar para `colaborador.user` → repetir → `/colaborador/data` vira **200**, `/admin/users` continua **403**
5. Mostrar a matriz de acesso no dashboard (admin/colaborador/visitante/anónimo vs. endpoints)

**O que realçar tecnicamente:**
- `require_role("colaborador", "admin")` aceita qualquer uma das roles listadas
- O role está no claim `realm_access.roles` dentro do JWT — a API nunca consulta o Keycloak em cada pedido
- HTTP 401 = sem token; HTTP 403 = token válido mas role insuficiente

**Transição:** *"O endpoint `/admin/mfa-area` tem uma exigência extra — precisa de MFA comprovado. Vamos ver isso agora."*

---

## Bloco 3 — MFA (TOTP) · `04:30 – 06:00`

**Frase de abertura:**
> "O `admin.user` tem MFA configurado como ação obrigatória no Keycloak. O Keycloak força o TOTP no browser flow."

**Passos:**
1. Logout do utilizador atual
2. Selecionar preset **`admin.user`** → clicar **Login**
3. O dashboard vai pedir o campo **TOTP** — abrir o Google Authenticator e copiar o código de 6 dígitos
4. Submeter → Login com sucesso
5. Mostrar o JWT: `amr: ["otp"]` ou `acr` no payload decoded
6. Tab **Autorização** → testar `/admin/mfa-area` → **200** ✅
7. Explicar: se o token não tiver `amr: otp`, o `require_mfa()` devolve **403**

**O que realçar tecnicamente:**
- `require_mfa()` em `app/auth.py` verifica o claim `amr` — procura `otp`, `mfa`, `2fa`, `google_authenticator`
- A lógica está inteiramente na API, não no Keycloak — o Keycloak apenas emite o claim
- `admin.user` tem `CONFIGURE_TOTP` como *required action* em `realm-export.json`

**Transição:** *"Agora o ciclo de vida dos utilizadores — Joiner, Mover, Leaver."*

---

## Bloco 4 — JML (Ciclo de Vida) · `06:00 – 08:30`

**Frase de abertura:**
> "O JML está implementado tanto em scripts CLI como em endpoints REST. Vamos usar o dashboard para demonstrar os três fluxos."

**Passos:**

**Joiner:**
1. Tab **JML** → Secção **Joiner**
2. Preencher: username `demo.user`, email `demo@empresa.pt`, role `visitante`, password `Demo@1234`
3. Clicar **Criar Utilizador**
4. Mostrar confirmação + ir à lista de utilizadores — `demo.user` aparece

**Mover:**
5. Secção **Mover** → username `demo.user`, role antiga `visitante`, role nova `colaborador`
6. Clicar **Mover Utilizador**
7. Mostrar mensagem: sessões revogadas → `demo.user` teria de fazer login novamente para obter novo token com a role correta
8. Verificar na lista de utilizadores que a role mudou

**Leaver:**
9. Secção **Leaver** → username `demo.user`
10. Clicar **Desativar Utilizador**
11. Mostrar confirmação: `enabled: false` — `demo.user` já não consegue autenticar

**O que realçar tecnicamente:**
- O Mover revoga sessões via `DELETE /admin/realms/iam-tp/users/{id}/sessions` — sem esperar pela expiração do token (default 300s)
- O Leaver não apaga o utilizador — apenas desativa e remove roles; o histórico de auditoria fica preservado
- O mesmo código está disponível como CLI: `python jml/joiner.py --username demo.user ...`

**Transição:** *"Todos estes eventos ficaram registados. Vamos ver a auditoria."*

---

## Bloco 5 — Auditoria · `08:30 – 09:30`

**Frase de abertura:**
> "O Keycloak regista automaticamente todos os eventos de autenticação e de administração. A nossa API expõe-nos de forma filtrada."

**Passos:**
1. Tab **Auditoria**
2. Filtro de tipo → selecionar **LOGIN** → mostrar tabela com username, IP, timestamp dos logins feitos durante a demo
3. Alterar filtro para **LOGIN_ERROR** → mostrar tentativas falhadas (se existirem)
4. Clicar **Summary** → mostrar gráfico de barras com contagens por tipo de evento
5. Descer para **Admin Events** → mostrar as operações JML (CREATE_USER, UPDATE_USER, DELETE_USER_ROLE_MAPPING) com o timestamp e utilizador afetado

**O que realçar tecnicamente:**
- Endpoint `GET /admin/audit` agrega eventos de utilizadores e de admin do Keycloak numa única resposta
- O Keycloak guarda os eventos no PostgreSQL — persistem mesmo após restart
- Em produção exportar-se-ia para um SIEM (ex: Splunk, ELK); aqui fica no Keycloak por simplicidade

**Transição:** *"Para fechar, um resumo rápido da arquitetura."*

---

## Bloco 6 — Fecho · `09:30 – 10:00`

**Frase de abertura:**
> "Em resumo: Keycloak como IdP central, FastAPI como resource server, PostgreSQL como backend. Tudo reproducível com `docker compose up` e `realm-export.json`."

**Passos:**
1. Tab **Arquitetura** → mostrar diagrama de componentes
2. Apontar os critérios de avaliação cobertos (tabela no dashboard ou na apresentação)
3. Mencionar: testes automáticos em `tests/test_auth.py` sem serviços reais (JWKS mockado)
4. Oferecer para responder a perguntas

**Critérios cobertos na demo:**

| Critério | Bloco | Peso |
|---|---|---|
| Arquitetura e coerência técnica | 0, 6 | 20% |
| Autenticação / Federação | 1 | 15% |
| Autorização | 2 | 15% |
| MFA | 3 | 15% |
| JML | 4 | 15% |
| Auditoria e segurança operacional | 5 | 10% |
| Qualidade da demo e comunicação | todos | 10% |

---

## Notas de Contingência

| Problema | Solução |
|---|---|
| Keycloak não arranca | `docker compose down -v && docker compose up` (apaga volumes e reimporta realm) |
| TOTP inválido | Verificar sincronização de hora no telemóvel; aguardar novo código (30s) |
| Token expirado durante demo | Clicar Logout e fazer login novamente no dashboard |
| Dashboard não carrega | Verificar `docker compose ps` — o `app` pode não estar healthy; `docker compose restart app` |
| Eventos de auditoria vazios | Fazer logout/login manual com os 3 utilizadores para gerar eventos antes da demo |
