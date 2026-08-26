"""Financial account API integration tests."""

from __future__ import annotations

import uuid

from httpx import AsyncClient

API = "/api/v1/accounts"
VALID_PASSWORD = "SecurePass1"


def _account_payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "name": f"Account-{uuid.uuid4().hex[:8]}",
        "account_type": "bank",
        "currency": "USD",
        "opening_balance": "1000.0000",
    }
    base.update(overrides)
    return base


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


async def test_create_account_success(authenticated_client: AsyncClient) -> None:
    payload = _account_payload(name="Checking")
    response = await authenticated_client.post(API, json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Checking"
    assert body["account_type"] == "bank"
    assert body["currency"] == "USD"
    assert body["opening_balance"] == "1000.0000"
    assert body["current_balance"] == "1000.0000"
    assert body["status"] == "active"
    assert body["archived_at"] is None


async def test_create_account_invalid_currency(
    authenticated_client: AsyncClient,
) -> None:
    response = await authenticated_client.post(
        API,
        json=_account_payload(currency="123"),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_CURRENCY"


async def test_create_account_duplicate_name(
    authenticated_client: AsyncClient,
) -> None:
    payload = _account_payload(name="Duplicate")
    first = await authenticated_client.post(API, json=payload)
    assert first.status_code == 201

    second = await authenticated_client.post(API, json=payload)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "ACCOUNT_NAME_CONFLICT"


async def test_list_accounts_paginated(authenticated_client: AsyncClient) -> None:
    for index in range(3):
        response = await authenticated_client.post(
            API,
            json=_account_payload(name=f"List-{index}"),
        )
        assert response.status_code == 201

    response = await authenticated_client.get(f"{API}?page=1&page_size=2")
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 2
    assert body["page"] == 1
    assert body["page_size"] == 2
    assert body["total_items"] >= 3
    assert body["total_pages"] >= 2


async def test_get_account(authenticated_client: AsyncClient) -> None:
    created = await authenticated_client.post(
        API,
        json=_account_payload(name="Retrieve Me"),
    )
    account_id = created.json()["id"]

    response = await authenticated_client.get(f"{API}/{account_id}")
    assert response.status_code == 200
    assert response.json()["id"] == account_id
    assert response.json()["name"] == "Retrieve Me"


async def test_update_account(authenticated_client: AsyncClient) -> None:
    created = await authenticated_client.post(
        API,
        json=_account_payload(name="Old Name"),
    )
    account_id = created.json()["id"]

    response = await authenticated_client.patch(
        f"{API}/{account_id}",
        json={"name": "New Name", "account_type": "savings"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "New Name"
    assert body["account_type"] == "savings"


async def test_update_account_requires_field(
    authenticated_client: AsyncClient,
) -> None:
    created = await authenticated_client.post(API, json=_account_payload())
    account_id = created.json()["id"]

    response = await authenticated_client.patch(f"{API}/{account_id}", json={})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_archive_account(authenticated_client: AsyncClient) -> None:
    created = await authenticated_client.post(
        API,
        json=_account_payload(name="To Archive"),
    )
    account_id = created.json()["id"]

    archived = await authenticated_client.post(f"{API}/{account_id}/archive")
    assert archived.status_code == 200
    body = archived.json()
    assert body["status"] == "archived"
    assert body["archived_at"] is not None

    still_visible = await authenticated_client.get(f"{API}/{account_id}")
    assert still_visible.status_code == 200
    assert still_visible.json()["status"] == "archived"

    active_only = await authenticated_client.get(f"{API}?status=active")
    active_ids = {item["id"] for item in active_only.json()["items"]}
    assert account_id not in active_ids

    archived_only = await authenticated_client.get(f"{API}?status=archived")
    archived_ids = {item["id"] for item in archived_only.json()["items"]}
    assert account_id in archived_ids


async def test_cannot_update_archived_account(
    authenticated_client: AsyncClient,
) -> None:
    created = await authenticated_client.post(API, json=_account_payload())
    account_id = created.json()["id"]
    await authenticated_client.post(f"{API}/{account_id}/archive")

    response = await authenticated_client.patch(
        f"{API}/{account_id}",
        json={"name": "Should Fail"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "ACCOUNT_ARCHIVED"


async def test_account_ownership_enforced(auth_client: AsyncClient) -> None:
    owner_token = await _register_token(auth_client, prefix="owner")
    other_token = await _register_token(auth_client, prefix="other")

    created = await auth_client.post(
        API,
        json=_account_payload(name="Private"),
        headers=_auth_headers(owner_token),
    )
    account_id = created.json()["id"]

    for method, url, kwargs in (
        ("get", f"{API}/{account_id}", {}),
        ("patch", f"{API}/{account_id}", {"json": {"name": "Hacked"}}),
        ("post", f"{API}/{account_id}/archive", {}),
    ):
        response = await getattr(auth_client, method)(
            url,
            headers=_auth_headers(other_token),
            **kwargs,
        )
        assert response.status_code == 404, response.text
        assert response.json()["error"]["code"] == "ACCOUNT_NOT_FOUND"


async def test_accounts_require_authentication(auth_client: AsyncClient) -> None:
    auth_client.headers.pop("Authorization", None)

    for method, url, kwargs in (
        ("post", API, {"json": _account_payload()}),
        ("get", API, {}),
        ("get", f"{API}/{uuid.uuid4()}", {}),
        ("patch", f"{API}/{uuid.uuid4()}", {"json": {"name": "X"}}),
        ("post", f"{API}/{uuid.uuid4()}/archive", {}),
    ):
        response = await getattr(auth_client, method)(url, **kwargs)
        assert response.status_code == 401, response.text
        assert response.json()["error"]["code"] == "UNAUTHORIZED"
