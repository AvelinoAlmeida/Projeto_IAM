import asyncio
import base64
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt

import auth


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _make_jwk(public_key, kid: str = "test-key") -> dict:
    numbers = public_key.public_numbers()
    n = numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, "big")
    e = numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, "big")
    return {
        "kty": "RSA",
        "kid": kid,
        "use": "sig",
        "alg": "RS256",
        "n": _b64url(n),
        "e": _b64url(e),
    }


def _make_token(private_key, kid: str, issuer: str, audience: str, extra_claims: dict = None) -> str:
    payload = {
        "sub": "123",
        "preferred_username": "tester",
        "realm_access": {"roles": ["admin"]},
        "iss": issuer,
        "aud": audience,
    }
    if extra_claims:
        payload.update(extra_claims)

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return jwt.encode(payload, private_pem, algorithm="RS256", headers={"kid": kid})


def test_require_role_allows_admin():
    dep = auth.require_role("admin")
    result = asyncio.run(dep({"realm_access": {"roles": ["admin"]}}))
    assert result["realm_access"]["roles"] == ["admin"]


def test_require_role_denies_non_admin():
    dep = auth.require_role("admin")
    with pytest.raises(Exception) as excinfo:
        asyncio.run(dep({"realm_access": {"roles": ["visitante"]}}))
    assert "Acesso negado" in str(excinfo.value)


def test_require_mfa_denies_without_otp():
    dep = auth.require_mfa()
    with pytest.raises(Exception) as excinfo:
        asyncio.run(dep({"amr": ["pwd"]}))
    assert "MFA" in str(excinfo.value)


def test_get_current_user_decodes_rs256_token():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    jwk = _make_jwk(public_key, kid="test-key")
    token = _make_token(private_key, "test-key", issuer="http://keycloak:8080/realms/iam-tp", audience="fastapi-client")

    class Cred:
        def __init__(self, credentials):
            self.credentials = credentials

    async def fake_get_jwks():
        return {"keys": [jwk]}

    with patch.object(auth, "_get_jwks", new=fake_get_jwks):
        user = asyncio.run(auth.get_current_user(Cred(token)))

    assert user["preferred_username"] == "tester"
    assert user["aud"] == "fastapi-client"
    assert user["iss"] == "http://localhost:8081/realms/iam-tp"
