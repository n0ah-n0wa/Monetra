"""Category API integration tests."""

from __future__ import annotations

import uuid

from app.services.default_categories import (
    DEFAULT_EXPENSE_CATEGORIES,
    DEFAULT_INCOME_CATEGORIES,
)
from httpx import AsyncClient

API = "/api/v1/categories"
VALID_PASSWORD = "SecurePass1"


def _category_payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "name": f"Category-{uuid.uuid4().hex[:8]}",
        "category_type": "expense",
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


async def test_list_includes_default_categories(
    authenticated_client: AsyncClient,
) -> None:
    response = await authenticated_client.get(
        f"{API}?include_system=false&page_size=100",
    )
    assert response.status_code == 200
    names = {(item["name"], item["category_type"]) for item in response.json()["items"]}
    for name in DEFAULT_EXPENSE_CATEGORIES:
        assert (name, "expense") in names
    for name in DEFAULT_INCOME_CATEGORIES:
        assert (name, "income") in names


async def test_create_category_success(authenticated_client: AsyncClient) -> None:
    payload = _category_payload(
        name="Side Projects",
        category_type="income",
        icon="briefcase",
        color="#336699",
    )
    response = await authenticated_client.post(API, json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Side Projects"
    assert body["category_type"] == "income"
    assert body["icon"] == "briefcase"
    assert body["color"] == "#336699"
    assert body["is_system"] is False
    assert body["status"] == "active"


async def test_create_category_rejects_universal_type(
    authenticated_client: AsyncClient,
) -> None:
    response = await authenticated_client.post(
        API,
        json=_category_payload(category_type="universal"),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_CATEGORY_TYPE"


async def test_create_category_duplicate_name_same_type(
    authenticated_client: AsyncClient,
) -> None:
    payload = _category_payload(name="Duplicate Cat", category_type="expense")
    first = await authenticated_client.post(API, json=payload)
    assert first.status_code == 201

    second = await authenticated_client.post(API, json=payload)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "CATEGORY_NAME_CONFLICT"


async def test_same_name_different_type_allowed(
    authenticated_client: AsyncClient,
) -> None:
    name = f"Shared-{uuid.uuid4().hex[:6]}"
    expense = await authenticated_client.post(
        API,
        json=_category_payload(name=name, category_type="expense"),
    )
    income = await authenticated_client.post(
        API,
        json=_category_payload(name=name, category_type="income"),
    )
    assert expense.status_code == 201
    assert income.status_code == 201


async def test_list_categories_filter_by_type(
    authenticated_client: AsyncClient,
) -> None:
    response = await authenticated_client.get(
        f"{API}?category_type=income&include_system=false&page_size=100",
    )
    assert response.status_code == 200
    assert all(item["category_type"] == "income" for item in response.json()["items"])


async def test_update_category(authenticated_client: AsyncClient) -> None:
    created = await authenticated_client.post(
        API,
        json=_category_payload(name="Old Label"),
    )
    category_id = created.json()["id"]

    response = await authenticated_client.patch(
        f"{API}/{category_id}",
        json={"name": "New Label", "icon": "star", "color": "#ff0000"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "New Label"
    assert body["icon"] == "star"
    assert body["color"] == "#ff0000"


async def test_update_category_requires_field(
    authenticated_client: AsyncClient,
) -> None:
    created = await authenticated_client.post(API, json=_category_payload())
    category_id = created.json()["id"]

    response = await authenticated_client.patch(f"{API}/{category_id}", json={})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_archive_category(authenticated_client: AsyncClient) -> None:
    created = await authenticated_client.post(
        API,
        json=_category_payload(name="Archive Me"),
    )
    category_id = created.json()["id"]

    archived = await authenticated_client.post(f"{API}/{category_id}/archive")
    assert archived.status_code == 200
    body = archived.json()
    assert body["status"] == "archived"
    assert body["archived_at"] is not None

    active_only = await authenticated_client.get(f"{API}?status=active")
    active_ids = {item["id"] for item in active_only.json()["items"]}
    assert category_id not in active_ids

    archived_only = await authenticated_client.get(f"{API}?status=archived")
    archived_ids = {item["id"] for item in archived_only.json()["items"]}
    assert category_id in archived_ids


async def test_cannot_update_archived_category(
    authenticated_client: AsyncClient,
) -> None:
    created = await authenticated_client.post(API, json=_category_payload())
    category_id = created.json()["id"]
    await authenticated_client.post(f"{API}/{category_id}/archive")

    response = await authenticated_client.patch(
        f"{API}/{category_id}",
        json={"name": "Should Fail"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CATEGORY_ARCHIVED"


async def test_category_ownership_enforced(auth_client: AsyncClient) -> None:
    owner_token = await _register_token(auth_client, prefix="owner")
    other_token = await _register_token(auth_client, prefix="other")

    created = await auth_client.post(
        API,
        json=_category_payload(name="Private Category"),
        headers=_auth_headers(owner_token),
    )
    category_id = created.json()["id"]

    for method, url, kwargs in (
        ("patch", f"{API}/{category_id}", {"json": {"name": "Hacked"}}),
        ("post", f"{API}/{category_id}/archive", {}),
    ):
        response = await getattr(auth_client, method)(
            url,
            headers=_auth_headers(other_token),
            **kwargs,
        )
        assert response.status_code == 404, response.text
        assert response.json()["error"]["code"] == "CATEGORY_NOT_FOUND"


async def test_categories_require_authentication(auth_client: AsyncClient) -> None:
    auth_client.headers.pop("Authorization", None)

    for method, url, kwargs in (
        ("post", API, {"json": _category_payload()}),
        ("get", API, {}),
        ("patch", f"{API}/{uuid.uuid4()}", {"json": {"name": "X"}}),
        ("post", f"{API}/{uuid.uuid4()}/archive", {}),
    ):
        response = await getattr(auth_client, method)(url, **kwargs)
        assert response.status_code == 401, response.text
        assert response.json()["error"]["code"] == "UNAUTHORIZED"
