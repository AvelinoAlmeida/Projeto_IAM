from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import admin, colaborador, public

app = FastAPI(
    title="IAM TP — Gestão de Identidade",
    description="Trabalho Prático MEI — Keycloak + FastAPI",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(public.router)
app.include_router(colaborador.router)
app.include_router(admin.router)
