"""API error handling tests."""

from app.core.exceptions import NotFoundError
from app.main import create_app
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel


class _Payload(BaseModel):
    amount: int


async def test_app_error_returns_standard_shape(app_settings) -> None:
    application = create_app(settings=app_settings)

    @application.get("/_test/not-found")
    async def raise_not_found() -> None:
        raise NotFoundError(
            code="TRANSACTION_NOT_FOUND",
            message="Transaction was not found.",
        )

    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/_test/not-found",
            headers={"X-Request-ID": "err-1"},
        )

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "TRANSACTION_NOT_FOUND"
    assert body["error"]["message"] == "Transaction was not found."
    assert body["error"]["details"] == {}
    assert body["request_id"] == "err-1"


async def test_http_exception_uses_error_envelope(app_settings) -> None:
    application = create_app(settings=app_settings)

    @application.get("/_test/http-error")
    async def raise_http() -> None:
        raise HTTPException(status_code=400, detail="Bad input")

    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/_test/http-error")

    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "HTTP_ERROR"
    assert body["error"]["message"] == "Bad input"
    assert "request_id" in body


async def test_validation_error_shape(app_settings) -> None:
    application = create_app(settings=app_settings)

    @application.post("/_test/validate")
    async def validate(payload: _Payload) -> _Payload:
        return payload

    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/_test/validate", json={"amount": "nope"})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "errors" in body["error"]["details"]


async def test_unhandled_error_hides_internals(app_settings) -> None:
    application = create_app(settings=app_settings)

    @application.get("/_test/boom")
    async def boom() -> None:
        raise RuntimeError("secret internals")

    # ServerErrorMiddleware re-raises after emitting the 500 response so the
    # process can log it; disable raise_app_exceptions to assert the body.
    transport = ASGITransport(app=application, raise_app_exceptions=False)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"X-Request-ID": "boom-1"},
    ) as client:
        response = await client.get("/_test/boom")

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert body["error"]["message"] == "An unexpected error occurred."
    assert "secret" not in response.text
    assert body["request_id"] == "boom-1"
