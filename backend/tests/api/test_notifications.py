"""Notification API integration tests."""

from __future__ import annotations

import uuid
from io import BytesIO

from app.models.enums import NotificationType
from httpx import AsyncClient

API = "/api/v1/notifications"
ACCOUNTS_API = "/api/v1/accounts"
BUDGETS_API = "/api/v1/budgets"
CATEGORIES_API = "/api/v1/categories"
GOALS_API = "/api/v1/goals"
TRANSACTIONS_API = "/api/v1/transactions"
IMPORTS_API = "/api/v1/imports"
RECURRING_API = "/api/v1/recurring-transactions"
VALID_PASSWORD = "SecurePass1"

CSV_HEADER = (
    "transaction_date,transaction_type,amount,description,category,"
    "external_reference,notes\n"
)


async def _register(client: AsyncClient, prefix: str = "n") -> tuple[str, str]:
    email = f"{prefix}-{uuid.uuid4().hex[:12]}@example.com"
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": VALID_PASSWORD},
    )
    assert response.status_code == 201, response.text
    return response.json()["access_token"], email


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _account(client: AsyncClient, token: str, name: str = "Cash") -> str:
    response = await client.post(
        ACCOUNTS_API,
        json={
            "name": f"{name}-{uuid.uuid4().hex[:6]}",
            "account_type": "bank",
            "currency": "USD",
            "opening_balance": "1000.0000",
        },
        headers=_auth(token),
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _category(
    client: AsyncClient,
    token: str,
    *,
    name: str,
    category_type: str,
) -> str:
    response = await client.get(
        f"{CATEGORIES_API}?include_system=false&page_size=100",
        headers=_auth(token),
    )
    assert response.status_code == 200
    for item in response.json()["items"]:
        if item["name"] == name and item["category_type"] == category_type:
            return item["id"]
    raise AssertionError(f"missing category {name}")


async def test_preferences_defaults_and_update(auth_client: AsyncClient) -> None:
    token, _ = await _register(auth_client)
    got = await auth_client.get(f"{API}/preferences", headers=_auth(token))
    assert got.status_code == 200, got.text
    body = got.json()
    assert body["budget_warning_enabled"] is True
    assert body["email_enabled"] is False

    patched = await auth_client.patch(
        f"{API}/preferences",
        json={"email_enabled": True, "import_completed_enabled": False},
        headers=_auth(token),
    )
    assert patched.status_code == 200
    assert patched.json()["email_enabled"] is True
    assert patched.json()["import_completed_enabled"] is False


async def test_list_mark_read_and_ownership(
    auth_client: AsyncClient,
    notification_provider,
) -> None:
    token_a, _ = await _register(auth_client, "a")
    token_b, _ = await _register(auth_client, "b")
    account = await _account(auth_client, token_a)
    groceries = await _category(
        auth_client, token_a, name="Groceries", category_type="expense"
    )

    budget = await auth_client.post(
        BUDGETS_API,
        json={
            "name": "Groceries Budget",
            "amount": "100.0000",
            "currency": "USD",
            "period": "monthly",
            "scope": "category",
            "start_date": "2026-01-01",
            "warning_threshold_percent": 80,
            "category_ids": [groceries],
        },
        headers=_auth(token_a),
    )
    assert budget.status_code == 201, budget.text

    spend = await auth_client.post(
        TRANSACTIONS_API,
        json={
            "account_id": account,
            "category_id": groceries,
            "transaction_type": "expense",
            "amount": "90.0000",
            "description": "Almost over",
            "transaction_date": "2026-01-15",
        },
        headers=_auth(token_a),
    )
    assert spend.status_code == 201, spend.text

    listed = await auth_client.get(API, headers=_auth(token_a))
    assert listed.status_code == 200
    assert listed.json()["total_items"] >= 1
    warning = next(
        item
        for item in listed.json()["items"]
        if item["notification_type"] == NotificationType.BUDGET_WARNING.value
    )
    assert warning["is_read"] is False

    other = await auth_client.get(
        f"{API}/{warning['id']}/read",
        headers=_auth(token_b),
    )
    # POST mark as read with wrong user via GET won't work; use POST
    other = await auth_client.post(
        f"{API}/{warning['id']}/read",
        headers=_auth(token_b),
    )
    assert other.status_code == 404

    marked = await auth_client.post(
        f"{API}/{warning['id']}/read",
        headers=_auth(token_a),
    )
    assert marked.status_code == 200
    assert marked.json()["is_read"] is True

    unread = await auth_client.get(
        f"{API}?unread_only=true",
        headers=_auth(token_a),
    )
    assert all(item["is_read"] is False for item in unread.json()["items"])


async def test_budget_exceeded_and_preference_suppresses(
    auth_client: AsyncClient,
) -> None:
    token, _ = await _register(auth_client, "bex")
    await auth_client.patch(
        f"{API}/preferences",
        json={"budget_exceeded_enabled": False},
        headers=_auth(token),
    )
    account = await _account(auth_client, token)
    groceries = await _category(
        auth_client, token, name="Groceries", category_type="expense"
    )
    budget = await auth_client.post(
        BUDGETS_API,
        json={
            "name": "Tiny",
            "amount": "10.0000",
            "currency": "USD",
            "period": "monthly",
            "scope": "category",
            "start_date": "2026-02-01",
            "warning_threshold_percent": 50,
            "category_ids": [groceries],
        },
        headers=_auth(token),
    )
    assert budget.status_code == 201, budget.text
    spend = await auth_client.post(
        TRANSACTIONS_API,
        json={
            "account_id": account,
            "category_id": groceries,
            "transaction_type": "expense",
            "amount": "15.0000",
            "description": "Over",
            "transaction_date": "2026-02-10",
        },
        headers=_auth(token),
    )
    assert spend.status_code == 201
    listed = await auth_client.get(API, headers=_auth(token))
    types = {item["notification_type"] for item in listed.json()["items"]}
    assert NotificationType.BUDGET_EXCEEDED.value not in types


async def test_goal_milestone_and_mark_all(
    auth_client: AsyncClient,
    notification_provider,
) -> None:
    token, email = await _register(auth_client, "goal")
    await auth_client.patch(
        f"{API}/preferences",
        json={"email_enabled": True},
        headers=_auth(token),
    )
    created = await auth_client.post(
        GOALS_API,
        json={
            "name": "Emergency",
            "target_amount": "100.0000",
            "current_amount": "50.0000",
            "currency": "USD",
        },
        headers=_auth(token),
    )
    assert created.status_code == 201, created.text
    goal_id = created.json()["id"]

    listed = await auth_client.get(API, headers=_auth(token))
    milestones = [
        item
        for item in listed.json()["items"]
        if item["notification_type"] == NotificationType.GOAL_MILESTONE.value
    ]
    assert {item["metadata"]["milestone_percent"] for item in milestones} == {25, 50}
    assert notification_provider.latest_app_notification() is not None
    assert notification_provider.latest_app_notification().to_email == email

    updated = await auth_client.patch(
        f"{GOALS_API}/{goal_id}",
        json={"current_amount": "100.0000"},
        headers=_auth(token),
    )
    assert updated.status_code == 200
    listed2 = await auth_client.get(API, headers=_auth(token))
    percents = {
        item["metadata"]["milestone_percent"]
        for item in listed2.json()["items"]
        if item["notification_type"] == NotificationType.GOAL_MILESTONE.value
    }
    assert percents == {25, 50, 75, 100}

    mark_all = await auth_client.post(f"{API}/read-all", headers=_auth(token))
    assert mark_all.status_code == 200
    assert mark_all.json()["updated_count"] >= 4
    unread = await auth_client.get(f"{API}?unread_only=true", headers=_auth(token))
    assert unread.json()["total_items"] == 0


async def test_import_completed_and_failed_notifications(
    auth_client: AsyncClient,
    monkeypatch,
) -> None:
    token, _ = await _register(auth_client, "imp")
    account = await _account(auth_client, token)
    csv = CSV_HEADER + "2026-03-01,expense,1.00,ok,Groceries,,\n"
    upload = await auth_client.post(
        IMPORTS_API,
        data={"account_id": account},
        files={"file": ("ok.csv", BytesIO(csv.encode("utf-8")), "text/csv")},
        headers=_auth(token),
    )
    assert upload.status_code == 201, upload.text
    confirm = await auth_client.post(
        f"{IMPORTS_API}/{upload.json()['id']}/confirm",
        headers=_auth(token),
    )
    assert confirm.status_code == 200
    listed = await auth_client.get(API, headers=_auth(token))
    types = [item["notification_type"] for item in listed.json()["items"]]
    assert NotificationType.IMPORT_COMPLETED.value in types

    upload2 = await auth_client.post(
        IMPORTS_API,
        data={"account_id": account},
        files={
            "file": (
                "fail.csv",
                BytesIO(
                    (
                        CSV_HEADER
                        + "2026-03-02,expense,1.00,one,Groceries,r1,\n"
                        + "2026-03-03,expense,1.00,two,Groceries,r2,\n"
                    ).encode("utf-8"),
                ),
                "text/csv",
            ),
        },
        headers=_auth(token),
    )
    assert upload2.status_code == 201
    from app.repositories import transaction_repository as txn_repo

    calls = {"n": 0}
    original = txn_repo.create_transaction

    async def flaky(*args, **kwargs):  # type: ignore[no-untyped-def]
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("boom")
        return await original(*args, **kwargs)

    monkeypatch.setattr(
        "app.services.import_service.transaction_repo.create_transaction",
        flaky,
    )
    failed = await auth_client.post(
        f"{IMPORTS_API}/{upload2.json()['id']}/confirm",
        headers=_auth(token),
    )
    assert failed.status_code == 422
    listed2 = await auth_client.get(API, headers=_auth(token))
    types2 = [item["notification_type"] for item in listed2.json()["items"]]
    assert NotificationType.IMPORT_FAILED.value in types2


async def test_recurring_executed_notification(auth_client: AsyncClient) -> None:
    token, _ = await _register(auth_client, "rec")
    account = await _account(auth_client, token)
    groceries = await _category(
        auth_client, token, name="Groceries", category_type="expense"
    )
    created = await auth_client.post(
        RECURRING_API,
        json={
            "account_id": account,
            "category_id": groceries,
            "transaction_type": "expense",
            "amount": "5.0000",
            "description": "Weekly snack",
            "frequency": "weekly",
            "start_date": "2026-01-01",
        },
        headers=_auth(token),
    )
    assert created.status_code == 201, created.text
    processed = await auth_client.post(
        f"{RECURRING_API}/process-due",
        json={"as_of_date": "2026-01-01"},
        headers=_auth(token),
    )
    assert processed.status_code == 200, processed.text
    assert any(item["created"] for item in processed.json()["executions"])
    listed = await auth_client.get(API, headers=_auth(token))
    types = {item["notification_type"] for item in listed.json()["items"]}
    assert NotificationType.RECURRING_CREATED.value in types
