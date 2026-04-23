from typing import Annotated

from fastapi import APIRouter, Depends

from auth import require_role

router = APIRouter(prefix="/colaborador", tags=["colaborador"])

_require = require_role("colaborador", "admin")


@router.get("/data")
async def colaborador_data(user: Annotated[dict, Depends(_require)]):
    return {
        "message": "Acesso permitido — área de colaboradores.",
        "user": user.get("preferred_username"),
        "roles": user.get("realm_access", {}).get("roles", []),
        "data": [
            {"id": 1, "doc": "Relatório Q1 2026"},
            {"id": 2, "doc": "Manual de Processos"},
            {"id": 3, "doc": "Dashboard de Vendas"},
        ],
    }


@router.get("/perfil")
async def colaborador_perfil(user: Annotated[dict, Depends(_require)]):
    return {
        "username": user.get("preferred_username"),
        "email": user.get("email"),
        "departamento": "Operações",
        "roles": user.get("realm_access", {}).get("roles", []),
    }
