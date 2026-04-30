import pathlib

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from routes import admin, colaborador, public

app = FastAPI(
    title="IAM TP — Gestão de Identidade",
    description="Trabalho Prático MEI — Keycloak + FastAPI",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8080",
        "http://localhost:8081",
        "null",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(public.router)
app.include_router(colaborador.router)
app.include_router(admin.router)

app.mount(
    "/static",
    StaticFiles(directory=pathlib.Path(__file__).parent / "static"),
    name="static",
)
