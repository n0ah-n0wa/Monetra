"""Configuration unit tests."""

import pytest
from app.core.config import Settings
from pydantic import ValidationError


def test_development_allows_default_secret() -> None:
    settings = Settings(
        app_env="development",
        jwt_secret_key="change-me-in-production-use-a-long-random-secret",
    )
    assert settings.is_development
    assert settings.docs_url == "/docs"
    assert settings.openapi_url == "/openapi.json"


def test_production_rejects_default_jwt_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(
            app_env="production",
            jwt_secret_key="change-me-in-production-use-a-long-random-secret",
            debug=False,
            cors_origins=["https://app.example.com"],
        )


def test_production_rejects_debug() -> None:
    with pytest.raises(ValidationError):
        Settings(
            app_env="production",
            jwt_secret_key="production-secret-key-with-enough-length",
            debug=True,
            cors_origins=["https://app.example.com"],
        )


def test_production_rejects_wildcard_cors() -> None:
    with pytest.raises(ValidationError):
        Settings(
            app_env="production",
            jwt_secret_key="production-secret-key-with-enough-length",
            debug=False,
            cors_origins=["*"],
        )


def test_production_disables_docs() -> None:
    settings = Settings(
        app_env="production",
        jwt_secret_key="production-secret-key-with-enough-length",
        debug=False,
        cors_origins=["https://app.example.com"],
    )
    assert settings.is_production
    assert settings.trusted_proxy_count == 1
    assert settings.refresh_token_cookie_secure is True
    assert settings.docs_url is None
    assert settings.redoc_url is None
    assert settings.openapi_url is None


def test_cors_origins_parse_csv() -> None:
    settings = Settings(
        app_env="test",
        cors_origins="http://a.example, http://b.example",  # type: ignore[arg-type]
        jwt_secret_key="test-secret-key-must-be-at-least-32-chars",
    )
    assert settings.cors_origins == ["http://a.example", "http://b.example"]
