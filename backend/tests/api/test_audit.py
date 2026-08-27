"""Audit logging API integration tests."""

from __future__ import annotations

import uuid
from io import BytesIO

from app.models.enums import AuditAction
from httpx import AsyncClient

AUDIT_API = "/api/v1/audit-events"
ACCOUNTS_API = "/api/v1/accounts"
BUDGETS_API = "/api/v1/budgets"
CATEGORIES_API = "/api/v1/categories"
TRANSACTIONS_API = "/api/v1/transactions"
TRANSFERS_API = "/api/v1/transfers"
IMPORTS_API = "/api/v1/imports"
VALID_PASSWORD = "SecurePass1"

CSV_HEADER = (
    "transaction_date,transaction_type,amount,description,category,"
    "external_reference,notes\n"
)


async def _register(client: AsyncClient, prefix: str = "aud") -> str:
    email = f"{prefix}-{uuid.uuid4().hex[:12]}@example.com"
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": VALID_PASSWORD},
    )
    assert response.status_code == 201, response.text
    return response.json()["access_token"]


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
    raise AssertionError(f"missing {name}")


async def _audit_actions(
    client: AsyncClient,
    token: str,
    *,
    entity_type: str | None = None,
) -> list[dict[str, object]]:
    query = f"{AUDIT_API}?page_size=100"
    if entity_type:
        query += f"&entity_type={entity_type}"
    response = await client.get(query, headers=_auth(token))
    assert response.status_code == 200, response.text
    return response.json()["items"]


async def test_transaction_lifecycle_audited(auth_client: AsyncClient) -> None:
    token = await _register(auth_client, "txn")
    account = await _account(auth_client, token)
    groceries = await _category(
        auth_client, token, name="Groceries", category_type="expense"
    )

    created = await auth_client.post(
        TRANSACTIONS_API,
        json={
            "account_id": account,
            "category_id": groceries,
            "transaction_type": "expense",
            "amount": "10.0000",
            "description": "Audit me",
            "transaction_date": "2026-01-10",
        },
        headers=_auth(token),
    )
    assert created.status_code == 201, created.text
    txn_id = created.json()["id"]

    updated = await auth_client.patch(
        f"{TRANSACTIONS_API}/{txn_id}",
        json={"amount": "12.0000"},
        headers=_auth(token),
    )
    assert updated.status_code == 200

    deleted = await auth_client.delete(
        f"{TRANSACTIONS_API}/{txn_id}",
        headers=_auth(token),
    )
    assert deleted.status_code == 204

    events = await _audit_actions(auth_client, token, entity_type="transaction")
    actions = [item["action"] for item in events if item["entity_id"] == txn_id]
    assert actions == [
        AuditAction.DELETED.value,
        AuditAction.UPDATED.value,
        AuditAction.CREATED.value,
    ]
    assert all(item["actor_id"] for item in events)
    assert all("password" not in (item.get("metadata") or {}) for item in events)


async def test_transfer_account_budget_import_audited(
    auth_client: AsyncClient,
) -> None:
    token = await _register(auth_client, "fin")
    source = await _account(auth_client, token, name="Src")
    dest = await _account(auth_client, token, name="Dst")
    groceries = await _category(
        auth_client, token, name="Groceries", category_type="expense"
    )

    transfer = await auth_client.post(
        TRANSFERS_API,
        json={
            "source_account_id": source,
            "destination_account_id": dest,
            "source_amount": "25.0000",
            "transaction_date": "2026-02-01",
            "description": "Move",
            "idempotency_key": f"key-{uuid.uuid4().hex}",
        },
        headers=_auth(token),
    )
    assert transfer.status_code == 201, transfer.text

    budget = await auth_client.post(
        BUDGETS_API,
        json={
            "name": "Audit Budget",
            "amount": "200.0000",
            "currency": "USD",
            "period": "monthly",
            "scope": "category",
            "start_date": "2026-01-01",
            "category_ids": [groceries],
        },
        headers=_auth(token),
    )
    assert budget.status_code == 201, budget.text
    budget_id = budget.json()["id"]

    patched = await auth_client.patch(
        f"{BUDGETS_API}/{budget_id}",
        json={"amount": "250.0000"},
        headers=_auth(token),
    )
    assert patched.status_code == 200

    archived_budget = await auth_client.post(
        f"{BUDGETS_API}/{budget_id}/archive",
        headers=_auth(token),
    )
    assert archived_budget.status_code == 200

    archived_account = await auth_client.post(
        f"{ACCOUNTS_API}/{dest}/archive",
        headers=_auth(token),
    )
    assert archived_account.status_code == 200

    csv = CSV_HEADER + "2026-03-01,expense,3.00,imported,Groceries,,\n"
    upload = await auth_client.post(
        IMPORTS_API,
        data={"account_id": source},
        files={"file": ("audit.csv", BytesIO(csv.encode("utf-8")), "text/csv")},
        headers=_auth(token),
    )
    assert upload.status_code == 201, upload.text
    confirm = await auth_client.post(
        f"{IMPORTS_API}/{upload.json()['id']}/confirm",
        headers=_auth(token),
    )
    assert confirm.status_code == 200, confirm.text

    all_events = await _audit_actions(auth_client, token)
    by_type: dict[str, set[str]] = {}
    for item in all_events:
        by_type.setdefault(str(item["entity_type"]), set()).add(str(item["action"]))

    assert AuditAction.CREATED.value in by_type["transfer"]
    assert AuditAction.CREATED.value in by_type["budget"]
    assert AuditAction.UPDATED.value in by_type["budget"]
    assert AuditAction.ARCHIVED.value in by_type["budget"]
    assert AuditAction.ARCHIVED.value in by_type["financial_account"]
    assert AuditAction.IMPORT_EXECUTED.value in by_type["import_job"]


async def test_audit_events_are_actor_scoped(auth_client: AsyncClient) -> None:
    token_a = await _register(auth_client, "aa")
    token_b = await _register(auth_client, "bb")
    account = await _account(auth_client, token_a)
    groceries = await _category(
        auth_client, token_a, name="Groceries", category_type="expense"
    )
    created = await auth_client.post(
        TRANSACTIONS_API,
        json={
            "account_id": account,
            "category_id": groceries,
            "transaction_type": "expense",
            "amount": "1.0000",
            "description": "private",
            "transaction_date": "2026-04-01",
        },
        headers=_auth(token_a),
    )
    assert created.status_code == 201

    listed_b = await auth_client.get(AUDIT_API, headers=_auth(token_b))
    assert listed_b.status_code == 200
    assert listed_b.json()["total_items"] == 0
