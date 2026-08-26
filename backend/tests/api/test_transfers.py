"""Transfer API integration tests."""

from __future__ import annotations

import uuid
from decimal import Decimal

from httpx import AsyncClient

API = "/api/v1/transfers"
ACCOUNTS_API = "/api/v1/accounts"
TRANSACTIONS_API = "/api/v1/transactions"
VALID_PASSWORD = "SecurePass1"


async def _register_token(client: AsyncClient, prefix: str = "user") -> str:
    email = f"{prefix}-{uuid.uuid4().hex[:12]}@example.com"
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": VALID_PASSWORD},
    )
    assert response.status_code == 201, response.text
    return response.json()["access_token"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _create_account(
    client: AsyncClient,
    token: str,
    *,
    name: str,
    currency: str = "USD",
    opening_balance: str = "1000.0000",
) -> str:
    response = await client.post(
        ACCOUNTS_API,
        json={
            "name": name,
            "account_type": "bank",
            "currency": currency,
            "opening_balance": opening_balance,
        },
        headers=_auth_headers(token),
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _account_balance(
    client: AsyncClient,
    token: str,
    account_id: str,
) -> Decimal:
    response = await client.get(
        f"{ACCOUNTS_API}/{account_id}",
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    return Decimal(response.json()["current_balance"])


def _transfer_payload(
    *,
    source_account_id: str,
    destination_account_id: str,
    source_amount: str = "100.0000",
    **overrides: object,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "source_account_id": source_account_id,
        "destination_account_id": destination_account_id,
        "source_amount": source_amount,
        "transaction_date": "2026-02-10",
        "description": "Test transfer",
    }
    payload.update(overrides)
    return payload


async def test_same_currency_transfer_updates_both_balances(
    auth_client: AsyncClient,
) -> None:
    token = await _register_token(auth_client)
    source_id = await _create_account(
        auth_client,
        token,
        name=f"Source-{uuid.uuid4().hex[:6]}",
    )
    destination_id = await _create_account(
        auth_client,
        token,
        name=f"Dest-{uuid.uuid4().hex[:6]}",
    )

    response = await auth_client.post(
        API,
        json=_transfer_payload(
            source_account_id=source_id,
            destination_account_id=destination_id,
            source_amount="150.2500",
        ),
        headers=_auth_headers(token),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["source_amount"] == "150.2500"
    assert body["destination_amount"] == "150.2500"
    assert body["exchange_rate"] is None

    assert await _account_balance(auth_client, token, source_id) == Decimal(
        "849.7500",
    )
    assert await _account_balance(auth_client, token, destination_id) == Decimal(
        "1150.2500",
    )


async def test_cross_currency_transfer_records_exchange_rate(
    auth_client: AsyncClient,
) -> None:
    token = await _register_token(auth_client)
    usd_id = await _create_account(
        auth_client,
        token,
        name=f"USD-{uuid.uuid4().hex[:6]}",
        currency="USD",
    )
    eur_id = await _create_account(
        auth_client,
        token,
        name=f"EUR-{uuid.uuid4().hex[:6]}",
        currency="EUR",
        opening_balance="0.0000",
    )

    response = await auth_client.post(
        API,
        json=_transfer_payload(
            source_account_id=usd_id,
            destination_account_id=eur_id,
            source_amount="200.0000",
            exchange_rate="0.85000000",
        ),
        headers=_auth_headers(token),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["source_currency"] == "USD"
    assert body["destination_currency"] == "EUR"
    assert body["destination_amount"] == "170.0000"
    assert body["exchange_rate"] == "0.85000000"


async def test_insufficient_balance_rejects_transfer_without_side_effects(
    auth_client: AsyncClient,
) -> None:
    token = await _register_token(auth_client)
    source_id = await _create_account(
        auth_client,
        token,
        name=f"Low-{uuid.uuid4().hex[:6]}",
        opening_balance="50.0000",
    )
    destination_id = await _create_account(
        auth_client,
        token,
        name=f"Target-{uuid.uuid4().hex[:6]}",
    )

    response = await auth_client.post(
        API,
        json=_transfer_payload(
            source_account_id=source_id,
            destination_account_id=destination_id,
            source_amount="100.0000",
        ),
        headers=_auth_headers(token),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INSUFFICIENT_BALANCE"

    assert await _account_balance(auth_client, token, source_id) == Decimal("50.0000")
    assert await _account_balance(auth_client, token, destination_id) == Decimal(
        "1000.0000",
    )

    listed = await auth_client.get(API, headers=_auth_headers(token))
    assert listed.json()["total_items"] == 0


async def test_same_account_transfer_rejected(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    account_id = await _create_account(
        auth_client,
        token,
        name=f"Solo-{uuid.uuid4().hex[:6]}",
    )

    response = await auth_client.post(
        API,
        json=_transfer_payload(
            source_account_id=account_id,
            destination_account_id=account_id,
        ),
        headers=_auth_headers(token),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "SAME_ACCOUNT_TRANSFER"


async def test_transfer_requires_owned_accounts(auth_client: AsyncClient) -> None:
    owner_token = await _register_token(auth_client, prefix="owner")
    other_token = await _register_token(auth_client, prefix="other")

    owner_source = await _create_account(
        auth_client,
        owner_token,
        name=f"Owner-{uuid.uuid4().hex[:6]}",
    )
    owner_dest = await _create_account(
        auth_client,
        owner_token,
        name=f"OwnerDest-{uuid.uuid4().hex[:6]}",
    )
    other_dest = await _create_account(
        auth_client,
        other_token,
        name=f"Other-{uuid.uuid4().hex[:6]}",
    )

    blocked = await auth_client.post(
        API,
        json=_transfer_payload(
            source_account_id=owner_source,
            destination_account_id=other_dest,
        ),
        headers=_auth_headers(owner_token),
    )
    assert blocked.status_code == 404
    assert blocked.json()["error"]["code"] == "ACCOUNT_NOT_FOUND"

    blocked_reverse = await auth_client.post(
        API,
        json=_transfer_payload(
            source_account_id=owner_source,
            destination_account_id=owner_dest,
        ),
        headers=_auth_headers(other_token),
    )
    assert blocked_reverse.status_code == 404


async def test_idempotent_transfer_request_returns_existing(
    auth_client: AsyncClient,
) -> None:
    token = await _register_token(auth_client)
    source_id = await _create_account(
        auth_client, token, name=f"A-{uuid.uuid4().hex[:6]}"
    )
    destination_id = await _create_account(
        auth_client,
        token,
        name=f"B-{uuid.uuid4().hex[:6]}",
    )
    payload = _transfer_payload(
        source_account_id=source_id,
        destination_account_id=destination_id,
        idempotency_key="transfer-key-001",
    )

    first = await auth_client.post(API, json=payload, headers=_auth_headers(token))
    assert first.status_code == 201
    transfer_id = first.json()["id"]

    second = await auth_client.post(API, json=payload, headers=_auth_headers(token))
    assert second.status_code == 200
    assert second.json()["id"] == transfer_id

    assert await _account_balance(auth_client, token, source_id) == Decimal("900.0000")
    assert await _account_balance(auth_client, token, destination_id) == Decimal(
        "1100.0000",
    )


async def test_idempotency_key_conflict_on_different_payload(
    auth_client: AsyncClient,
) -> None:
    token = await _register_token(auth_client)
    source_id = await _create_account(
        auth_client, token, name=f"A-{uuid.uuid4().hex[:6]}"
    )
    destination_id = await _create_account(
        auth_client,
        token,
        name=f"B-{uuid.uuid4().hex[:6]}",
    )

    first = await auth_client.post(
        API,
        json=_transfer_payload(
            source_account_id=source_id,
            destination_account_id=destination_id,
            source_amount="50.0000",
            idempotency_key="shared-key",
        ),
        headers=_auth_headers(token),
    )
    assert first.status_code == 201

    second = await auth_client.post(
        API,
        json=_transfer_payload(
            source_account_id=source_id,
            destination_account_id=destination_id,
            source_amount="75.0000",
            idempotency_key="shared-key",
        ),
        headers=_auth_headers(token),
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "IDEMPOTENCY_KEY_CONFLICT"


async def test_transfer_does_not_create_income_or_expense_transactions(
    auth_client: AsyncClient,
) -> None:
    token = await _register_token(auth_client)
    source_id = await _create_account(
        auth_client, token, name=f"A-{uuid.uuid4().hex[:6]}"
    )
    destination_id = await _create_account(
        auth_client,
        token,
        name=f"B-{uuid.uuid4().hex[:6]}",
    )

    before = await auth_client.get(TRANSACTIONS_API, headers=_auth_headers(token))
    assert before.status_code == 200
    before_count = before.json()["total_items"]

    transfer = await auth_client.post(
        API,
        json=_transfer_payload(
            source_account_id=source_id,
            destination_account_id=destination_id,
        ),
        headers=_auth_headers(token),
    )
    assert transfer.status_code == 201

    after = await auth_client.get(TRANSACTIONS_API, headers=_auth_headers(token))
    assert after.json()["total_items"] == before_count


async def test_get_transfer_and_ownership(auth_client: AsyncClient) -> None:
    owner_token = await _register_token(auth_client, prefix="owner")
    other_token = await _register_token(auth_client, prefix="other")
    source_id = await _create_account(
        auth_client,
        owner_token,
        name=f"A-{uuid.uuid4().hex[:6]}",
    )
    destination_id = await _create_account(
        auth_client,
        owner_token,
        name=f"B-{uuid.uuid4().hex[:6]}",
    )

    created = await auth_client.post(
        API,
        json=_transfer_payload(
            source_account_id=source_id,
            destination_account_id=destination_id,
        ),
        headers=_auth_headers(owner_token),
    )
    transfer_id = created.json()["id"]

    owned = await auth_client.get(
        f"{API}/{transfer_id}",
        headers=_auth_headers(owner_token),
    )
    assert owned.status_code == 200

    blocked = await auth_client.get(
        f"{API}/{transfer_id}",
        headers=_auth_headers(other_token),
    )
    assert blocked.status_code == 404
    assert blocked.json()["error"]["code"] == "TRANSFER_NOT_FOUND"


async def test_transfers_require_authentication(auth_client: AsyncClient) -> None:
    auth_client.headers.pop("Authorization", None)

    response = await auth_client.post(
        API,
        json={
            "source_account_id": str(uuid.uuid4()),
            "destination_account_id": str(uuid.uuid4()),
            "source_amount": "10.0000",
            "transaction_date": "2026-02-10",
        },
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
