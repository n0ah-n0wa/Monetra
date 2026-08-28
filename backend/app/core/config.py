"""Application settings loaded from environment variables."""

from functools import lru_cache
from typing import Annotated, Literal, Self

from pydantic import Field, PostgresDsn, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_DEFAULT_JWT_SECRET = "change-me-in-production-use-a-long-random-secret"  # noqa: S105


class Settings(BaseSettings):
    """Runtime configuration for the Monetra backend.

    Development, test, and production are selected via ``APP_ENV``.
    Production rejects insecure defaults.
    """

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Monetra"
    app_env: Literal["development", "test", "production"] = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"
    api_description: str = (
        "Monetra personal finance platform API. "
        "Monetary values use exact decimal arithmetic."
    )

    database_url: PostgresDsn = Field(
        default=PostgresDsn(
            "postgresql+psycopg://monetra:monetra@localhost:5432/monetra"
        ),
    )
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_echo: bool = False

    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"],
    )

    jwt_secret_key: str = Field(default=_DEFAULT_JWT_SECRET, min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 14
    password_reset_token_expire_minutes: int = Field(default=60, ge=1)

    auth_password_min_length: int = Field(default=8, ge=8)
    auth_password_require_letter: bool = True
    auth_password_require_digit: bool = True

    refresh_token_cookie_name: str = "monetra_refresh_token"  # noqa: S105
    refresh_token_cookie_path: str = "/api/v1/auth"  # noqa: S105
    refresh_token_cookie_domain: str | None = None
    refresh_token_cookie_secure: bool = False
    refresh_token_cookie_samesite: Literal["lax", "strict", "none"] = "lax"  # noqa: S105

    auth_rate_limit_max_requests: int = Field(default=10, ge=1)
    auth_rate_limit_window_seconds: int = Field(default=60, ge=1)
    password_reset_email_rate_limit_max_requests: int = Field(default=3, ge=1)
    password_reset_request_cooldown_seconds: int = Field(default=300, ge=60)
    trusted_proxy_count: int = Field(default=0, ge=0)

    api_default_page_size: int = Field(default=20, ge=1)
    api_max_page_size: int = Field(default=100, ge=1)

    import_max_file_bytes: int = Field(default=5 * 1024 * 1024, ge=1024)
    import_max_rows: int = Field(default=10_000, ge=1)
    import_preview_limit: int = Field(default=50, ge=1)
    export_max_rows: int = Field(default=10_000, ge=1)

    exchange_rate_provider: Literal["none", "static", "test"] = "none"
    exchange_rate_static_rates: str = ""
    exchange_rate_cache_ttl_seconds: int = Field(default=300, ge=0)
    exchange_rate_allow_stale_on_failure: bool = True

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def validate_environment(self) -> Self:
        if self.app_env == "production":
            if self.jwt_secret_key == _DEFAULT_JWT_SECRET:
                msg = "JWT_SECRET_KEY must be set to a non-default value in production"
                raise ValueError(msg)
            if self.debug:
                msg = "DEBUG must be false when APP_ENV=production"
                raise ValueError(msg)
            if "*" in self.cors_origins:
                msg = "CORS_ORIGINS must not use wildcard '*' in production"
                raise ValueError(msg)
            object.__setattr__(self, "refresh_token_cookie_secure", True)
            if self.trusted_proxy_count < 1:
                object.__setattr__(self, "trusted_proxy_count", 1)
        return self

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_test(self) -> bool:
        return self.app_env == "test"

    @property
    def async_database_url(self) -> str:
        return str(self.database_url)

    @property
    def docs_url(self) -> str | None:
        return None if self.is_production else "/docs"

    @property
    def redoc_url(self) -> str | None:
        return None if self.is_production else "/redoc"

    @property
    def openapi_url(self) -> str | None:
        return None if self.is_production else "/openapi.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
