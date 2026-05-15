# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a LaTeX academic report (Portuguese) for the MEI — Gestão de Identidade course at ESTG-IPP (2025/2026), authored by Avelino Almeida (8220800). The report documents the design and implementation of an IAM platform built with Keycloak 26, FastAPI (Python 3.12), and PostgreSQL 16, orchestrated by Docker Compose.

**Submission deadline**: 28 de maio de 2026

## Building the Document

Compile from the repo root (where `main.tex` lives). A full build requires three passes for cross-references and the glossary:

```bash
pdflatex main
makeglossaries main
pdflatex main
pdflatex main
```

Or with `latexmk` (handles passes automatically):

```bash
latexmk -pdf -shell-escape main
```

`\graphicspath{{../imagens/}}` — images are expected in an `imagens/` sibling directory outside the repo root.

## Document Structure

**Entry point**: [main.tex](main.tex) — preamble, package setup, and `\input` directives.

**Chapters currently included** (in order):
| File | Content |
|------|---------|
| [capitulos/cap01_arquitetura.tex](capitulos/cap01_arquitetura.tex) | Architecture, components, deployment model |
| [capitulos/cap02_decisoes.tex](capitulos/cap02_decisoes.tex) | Technical decisions (JWT validation, RBAC, caching) |
| [capitulos/cap03_autenticacao.tex](capitulos/cap03_autenticacao.tex) | OIDC/OAuth 2.0 flows, JWT structure, JWKS |
| [capitulos/cap04_jml_mfa.tex](capitulos/cap04_jml_mfa.tex) | JML lifecycle flows and MFA/TOTP implementation |
| [capitulos/cap05_riscos.tex](capitulos/cap05_riscos.tex) | Risk assessment |

**Appendices** (already included):
- [anexos/anx01_realm.tex](anexos/anx01_realm.tex) — Keycloak realm-export.json walkthrough
- [anexos/anx02_utilizadores.tex](anexos/anx02_utilizadores.tex) — Test users and credentials
- [anexos/anx03_demo.tex](anexos/anx03_demo.tex) — 10-minute graded demonstration script

**Shared support files**:
- [acronimos.tex](acronimos.tex) — 35+ glossary/acronym definitions (`\newacronym`)
- [refs.tex](refs.tex) — BibTeX bibliography (IEEE format); compiled with `\bibliographystyle{ieeetr}`

## LaTeX Conventions

- Acronyms must be defined in [acronimos.tex](acronimos.tex) and referenced with `\gls{id}` (first use expands, subsequent uses abbreviate).
- Figures: `\begin{figure}[H]` with `\caption` and `\label{fig:...}`, referenced via `\ref{fig:...}`.
- Code listings: `\begin{lstlisting}[caption={...},label={lst:...}]` — the global `lstset` in `main.tex` applies.
- Bibliography keys follow the pattern `Author:YYYYkeyword` (e.g., `NIST:800-63B`, `RFC:6749`).

## Implemented Platform (described in the report, not in this repo)

The actual implementation lives outside this directory. Key commands referenced in the report:

```bash
docker compose up --build        # start full stack (Keycloak + FastAPI + PostgreSQL)
curl http://localhost:8000/health # verify FastAPI is running
python -m pytest tests/ -v       # run 4 unit tests (test_auth.py)
python jml/joiner.py             # Joiner flow (create user)
python jml/mover.py              # Mover flow (change role)
python jml/leaver.py             # Leaver flow (disable + revoke session)
```

Dashboard: `http://localhost:8000/dashboard` — live evidence for all assessment requirements.
