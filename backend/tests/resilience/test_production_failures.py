"""Production failure scenario regression tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from app.core.config import Settings
from app.core.security import create_access_token, hash_refresh_token
from app.domain.notifications import AppNotificationMessage
from app.main import create_app
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from tests.resilience.helpers import (
    CSV_HEADER,
    account_balance,
    auth_headers,
    create_account,
    register_token,
    upload_csv,
)

API = "/api/v1"
IMPORTS_API = f"{API}/imports"
TRANSACTIONS_API = f"{API}/transactions"
TRANSFERS_API = f"{API}/transfers"
EXCHANGE_RATES_API = f"{API}/exchange-rates"


class FailingNotificationProvider:
    """Test double that simulates an unavailable outbound notification channel."""

    async def send_password_reset(self, notification: object) -> None:
        raise RuntimeError("notification provider unavailable")

    async def send_app_notification(
        self,
        notification: AppNotificationMessage,
    ) -> None:
        raise RuntimeError("notification provider unavailable")


@pytest.mark.asyncio
async def test_ready_returns_503_when_postgresql_unavailable(
    client: AsyncClient,
) -> None:
    from app.db.session import DatabaseConnectivityResult

    unavailable = DatabaseConnectivityResult(
        ok=False,
        latency_ms=15.0,
        error="database_connection_failed",
    )
    with patch(
        "app.api.v1.health.check_database_connectivity",
        new=AsyncMock(return_value=unavailable),
    ):
        response = await client.get("/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "unavailable"
    assert body["database"] is False
    assert body["checks"]["database"]["error"] == "database_connection_failed"
    assert "password" not in response.text.lower()


@pytest.mark.asyncio
async def test_exchange_rate_provider_unavailable_returns_503(
    auth_client: AsyncClient,
) -> None:
    token = await register_token(auth_client, prefix="fx-fail")
    response = await auth_client.post(
        f"{EXCHANGE_RATES_API}/fetch",
        json={
            "base_currency": "EUR",
            "quote_currency": "USD",
            "rate_date": "2026-06-01",
        },
        headers=auth_headers(token),
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "EXCHANGE_RATE_PROVIDER_UNAVAILABLE"


@pytest.mark.asyncio
async def test_malformed_csv_preview_reports_errors_without_importing(
    auth_client: AsyncClient,
) -> None:
    token = await register_token(auth_client, prefix="csv-bad")
    account_id = await create_account(auth_client, token)
    balance_before = await account_balance(auth_client, token, account_id)

    csv = CSV_HEADER + (
        "not-a-date,expense,10.00,Bad row,Groceries,,\n"
        "2026-01-15,expense,not-money,Bad amount,Groceries,,\n"
    )
    upload = await upload_csv(
        auth_client,
        token,
        account_id=account_id,
        content=csv,
    )
    assert upload.status_code == 201, upload.text
    body = upload.json()
    assert body["stats"]["valid_rows"] == 0
    assert body["stats"]["invalid_rows"] == 2
    error_codes = {error["code"] for error in body["errors"]}
    assert "INVALID_TRANSACTION_DATE" in error_codes
    assert "INVALID_AMOUNT" in error_codes

    confirm = await auth_client.post(
        f"{IMPORTS_API}/{body['id']}/confirm",
        headers=auth_headers(token),
    )
    assert confirm.status_code == 200
    assert confirm.json()["stats"]["imported_rows"] == 0
    assert await account_balance(auth_client, token, account_id) == balance_before


@pytest.mark.asyncio
async def test_oversized_csv_rejected_without_side_effects(
    app_settings: Settings,
    auth_client: AsyncClient,
) -> None:
    small_app = create_app(
        settings=app_settings.model_copy(update={"import_max_file_bytes": 512}),
    )
    async with small_app.router.lifespan_context(small_app):
        transport = ASGITransport(app=small_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            token = await register_token(client, prefix="csv-big")
            account_id = await create_account(client, token)
            balance_before = await account_balance(client, token, account_id)
            big_csv = CSV_HEADER + ("2026-01-15,expense,1.00,Row,Groceries,,\n" * 40)
            assert len(big_csv.encode("utf-8")) > 512

            response = await upload_csv(
                client,
                token,
                account_id=account_id,
                content=big_csv,
            )
            assert response.status_code == 422
            assert response.json()["error"]["code"] == "FILE_TOO_LARGE"
            assert await account_balance(client, token, account_id) == balance_before


@pytest.mark.asyncio
async def test_expired_access_token_rejected_safely(
    auth_client: AsyncClient,
    app_settings: Settings,
) -> None:
    token = await register_token(auth_client, prefix="jwt-exp")
    profile = await auth_client.get(
        f"{API}/users/me",
        headers=auth_headers(token),
    )
    user_id = profile.json()["id"]
    expired = create_access_token(
        user_id,
        settings=app_settings,
        expires_delta=timedelta(seconds=-60),
    )
    response = await auth_client.get(
        f"{API}/users/me",
        headers=auth_headers(expired),
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_TOKEN"
    assert "secret" not in response.text.lower()


@pytest.mark.asyncio
async def test_expired_refresh_token_rejected(
    auth_client: AsyncClient,
    db_engine: AsyncEngine,
) -> None:
    await register_token(auth_client, prefix="refresh-exp")
    refresh_cookie = auth_client.cookies.get("monetra_refresh_token")
    assert refresh_cookie

    async with db_engine.begin() as connection:
        await connection.execute(
            text(
                "UPDATE refresh_tokens "
                "SET expires_at = :expired "
                "WHERE token_hash = :token_hash",
            ),
            {
                "expired": datetime.now(UTC) - timedelta(minutes=5),
                "token_hash": hash_refresh_token(refresh_cookie),
            },
        )

    response = await auth_client.post(f"{API}/auth/refresh")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_REFRESH_TOKEN"


@pytest.mark.asyncio
async def test_invalid_refresh_token_rejected(
    auth_client: AsyncClient,
) -> None:
    auth_client.cookies.set("monetra_refresh_token", "not-a-real-refresh-token")
    response = await auth_client.post(f"{API}/auth/refresh")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_REFRESH_TOKEN"


@pytest.mark.asyncio
async def test_duplicate_transfer_request_is_idempotent(
    auth_client: AsyncClient,
) -> None:
    token = await register_token(auth_client, prefix="dup-transfer")
    source_id = await create_account(auth_client, token, opening_balance="500.0000")
    dest_id = await create_account(auth_client, token)
    payload = {
        "source_account_id": source_id,
        "destination_account_id": dest_id,
        "source_amount": "50.0000",
        "transaction_date": "2026-06-01",
        "idempotency_key": f"dup-{uuid.uuid4().hex}",
    }

    first = await auth_client.post(
        TRANSFERS_API,
        json=payload,
        headers=auth_headers(token),
    )
    second = await auth_client.post(
        TRANSFERS_API,
        json=payload,
        headers=auth_headers(token),
    )
    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert await account_balance(auth_client, token, source_id) == Decimal("450.0000")
    assert await account_balance(auth_client, token, dest_id) == Decimal("1050.0000")


@pytest.mark.asyncio
async def test_failed_transaction_create_preserves_balance(
    application,
    auth_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = await register_token(auth_client, prefix="txn-fail")
    account_id = await create_account(auth_client, token)
    balance_before = await account_balance(auth_client, token, account_id)

    categories = await auth_client.get(
        f"{API}/categories?include_system=false&page_size=100",
        headers=auth_headers(token),
    )
    category_id = next(
        item["id"] for item in categories.json()["items"] if item["name"] == "Groceries"
    )

    async def failing_create(*args: object, **kwargs: object) -> object:
        raise RuntimeError("simulated persistence failure")

    monkeypatch.setattr(
        "app.services.transaction_service.transaction_repo.create_transaction",
        failing_create,
    )

    transport = ASGITransport(application, raise_app_exceptions=False)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers=auth_headers(token),
        cookies=auth_client.cookies,
    ) as client:
        response = await client.post(
            TRANSACTIONS_API,
            json={
                "account_id": account_id,
                "category_id": category_id,
                "transaction_type": "expense",
                "amount": "25.0000",
                "description": "Should not persist",
                "transaction_date": "2026-06-01",
            },
        )

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert "simulated" not in response.text
    assert await account_balance(auth_client, token, account_id) == balance_before

    listed = await auth_client.get(
        f"{TRANSACTIONS_API}?account_id={account_id}",
        headers=auth_headers(token),
    )
    assert listed.json()["total_items"] == 0


@pytest.mark.asyncio
async def test_failed_import_rolls_back_all_rows(
    auth_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = await register_token(auth_client, prefix="import-fail")
    account_id = await create_account(auth_client, token)
    balance_before = await account_balance(auth_client, token, account_id)
    csv = CSV_HEADER + (
        "2026-01-15,expense,10.00,One,Groceries,r1,\n"
        "2026-01-16,expense,20.00,Two,Groceries,r2,\n"
    )
    upload = await upload_csv(auth_client, token, account_id=account_id, content=csv)
    job_id = upload.json()["id"]

    from app.repositories import transaction_repository as txn_repo

    calls = {"n": 0}
    original = txn_repo.create_transaction

    async def flaky_create(*args: object, **kwargs: object) -> object:
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("simulated import failure")
        return await original(*args, **kwargs)

    monkeypatch.setattr(
        "app.services.import_service.transaction_repo.create_transaction",
        flaky_create,
    )

    confirm = await auth_client.post(
        f"{IMPORTS_API}/{job_id}/confirm",
        headers=auth_headers(token),
    )
    assert confirm.status_code == 422
    assert confirm.json()["error"]["code"] == "IMPORT_FAILED"
    assert await account_balance(auth_client, token, account_id) == balance_before

    job = await auth_client.get(
        f"{IMPORTS_API}/{job_id}",
        headers=auth_headers(token),
    )
    assert job.json()["status"] == "failed"
    assert job.json()["stats"]["imported_rows"] == 0


@pytest.mark.asyncio
async def test_import_failure_persists_even_when_notification_provider_unavailable(
    auth_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = await register_token(auth_client, prefix="notify-fail")
    account_id = await create_account(auth_client, token)
    balance_before = await account_balance(auth_client, token, account_id)
    csv = CSV_HEADER + "2026-01-15,expense,10.00,One,Groceries,r1,\n"
    upload = await upload_csv(auth_client, token, account_id=account_id, content=csv)
    job_id = upload.json()["id"]

    failing_provider = FailingNotificationProvider()
    monkeypatch.setattr(
        "app.api.deps.get_app_notification_provider",
        lambda _request: failing_provider,
    )

    async def failing_create(*args: object, **kwargs: object) -> object:
        raise RuntimeError("simulated import failure")

    monkeypatch.setattr(
        "app.services.import_service.transaction_repo.create_transaction",
        failing_create,
    )

    prefs = await auth_client.patch(
        f"{API}/notifications/preferences",
        json={"email_enabled": True},
        headers=auth_headers(token),
    )
    assert prefs.status_code == 200

    confirm = await auth_client.post(
        f"{IMPORTS_API}/{job_id}/confirm",
        headers=auth_headers(token),
    )
    assert confirm.status_code == 422
    assert confirm.json()["error"]["code"] == "IMPORT_FAILED"
    assert await account_balance(auth_client, token, account_id) == balance_before

    job = await auth_client.get(
        f"{IMPORTS_API}/{job_id}",
        headers=auth_headers(token),
    )
    assert job.json()["status"] == "failed"

    notifications = await auth_client.get(
        f"{API}/notifications",
        headers=auth_headers(token),
    )
    assert notifications.status_code == 200
    assert any(
        item["notification_type"] == "import_failed"
        for item in notifications.json()["items"]
    )
