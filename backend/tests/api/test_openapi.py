"""OpenAPI and application factory tests."""

from app.core.config import Settings
from app.main import create_app
from httpx import AsyncClient


async def test_openapi_available_in_non_production(client: AsyncClient) -> None:
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    payload = response.json()
    assert payload["info"]["title"] == "Monetra"
    assert "health" in {tag["name"] for tag in payload["tags"]}


def test_production_app_hides_openapi() -> None:
    settings = Settings(
        app_env="production",
        jwt_secret_key="production-secret-key-with-enough-length",
        debug=False,
        cors_origins=["https://app.example.com"],
    )
    application = create_app(settings=settings)
    assert application.docs_url is None
    assert application.openapi_url is None
