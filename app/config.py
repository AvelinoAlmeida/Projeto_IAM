from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    keycloak_url: str = "http://keycloak:8080"
    keycloak_issuer_url: str | None = None
    keycloak_realm: str = "iam-tp"
    keycloak_client_id: str = Field(
        default="fastapi-client",
        validation_alias=AliasChoices("KEYCLOAK_CLIENT_ID", "OIDC_CLIENT_ID"),
    )
    keycloak_client_secret: str = Field(
        default="",
        validation_alias=AliasChoices("KEYCLOAK_CLIENT_SECRET", "OIDC_CLIENT_SECRET"),
    )
    keycloak_admin_user: str = Field(
        default="admin",
        validation_alias=AliasChoices("KEYCLOAK_ADMIN_USER", "KEYCLOAK_ADMIN"),
    )
    keycloak_admin_password: str = ""
    keycloak_admin_realm: str = "master"
    keycloak_admin_client_id: str = "admin-cli"
    demo_admin_user: str = "admin.demo"
    demo_admin_pass: str = "Demo@1234"

    @property
    def oidc_config_url(self) -> str:
        return f"{self.keycloak_url}/realms/{self.keycloak_realm}/.well-known/openid-configuration"

    @property
    def jwks_uri(self) -> str:
        return f"{self.keycloak_url}/realms/{self.keycloak_realm}/protocol/openid-connect/certs"

    @property
    def issuer(self) -> str:
        issuer_base = self.keycloak_issuer_url or self.keycloak_url
        return f"{issuer_base}/realms/{self.keycloak_realm}"

    @property
    def admin_api_url(self) -> str:
        return f"{self.keycloak_url}/admin/realms/{self.keycloak_realm}"

    @property
    def token_url(self) -> str:
        return f"{self.keycloak_url}/realms/{self.keycloak_realm}/protocol/openid-connect/token"

    @property
    def admin_token_url(self) -> str:
        return f"{self.keycloak_url}/realms/{self.keycloak_admin_realm}/protocol/openid-connect/token"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
