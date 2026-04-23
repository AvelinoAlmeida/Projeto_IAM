from typing import Annotated

from fastapi import APIRouter, Depends

from auth import get_current_user

router = APIRouter(tags=["public"])


@router.get("/health")
async def health():
    return {"status": "ok", "service": "IAM TP — FastAPI"}


@router.get("/public")
async def public_resource():
    return {
        "message": "Este recurso é público — não requer autenticação.",
        "data": ["item_publico_1", "item_publico_2"],
    }


@router.get("/me")
async def me(user: Annotated[dict, Depends(get_current_user)]):
    return {
        "sub": user.get("sub"),
        "email": user.get("email"),
        "preferred_username": user.get("preferred_username"),
        "roles": user.get("realm_access", {}).get("roles", []),
        "name": user.get("name"),
    }
