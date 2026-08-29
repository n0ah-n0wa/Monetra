"""CSV import API integration tests."""

from __future__ import annotations

import uuid
from decimal import Decimal
from io import BytesIO

import pytest
from httpx import ASGITransport, AsyncClient

API = "/api/v1/imports"
ACCOUNTS_API = "/api/v1/accounts"
TRANSACTIONS_API = "/api/v1/transactions"
CATEGORIES_API = "/api/v1/categories"
VALID_PASSWORD = "SecurePass1"

CSV_HEADER = (
    "transaction_date,transaction_type,amount,description,category,"
    "external_reference,notes\n"
)


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
    name: str | None = None,
    opening_balance: str = "1000.0000",
) -> str:
    response = await client.post(
        ACCOUNTS_API,
        json={
            "name": name or f"Import-{uuid.uuid4().hex[:6]}",
            "account_type": "bank",
            "currency": "USD",
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


async def _upload(
    client: AsyncClient,
    token: str,
    *,
    account_id: str,
    content: str,
    filename: str = "import.csv",
    content_type: str = "text/csv",
) -> object:
    return await client.post(
        API,
        data={"account_id": account_id},
        files={"file": (filename, BytesIO(content.encode("utf-8")), content_type)},
        headers=_auth_headers(token),
    )


async def test_upload_preview_confirm_happy_path(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    account_id = await _create_account(auth_client, token)
    csv = CSV_HEADER + (
        "2026-01-15,expense,25.50,Coffee,Groceries,ref-coffee,\n"
        "2026-01-16,income,200.00,Bonus,Salary,,payday\n"
    )
    upload = await _upload(auth_client, token, account_id=account_id, content=csv)
    assert upload.status_code == 201, upload.text
    preview = upload.json()
    assert preview["status"] == "preview"
    assert preview["stats"]["total_rows"] == 2
    assert preview["stats"]["valid_rows"] == 2
    assert preview["stats"]["invalid_rows"] == 0
    assert preview["stats"]["duplicate_rows"] == 0
    assert len(preview["preview_rows"]) == 2

    job_id = preview["id"]
    confirm = await auth_client.post(
        f"{API}/{job_id}/confirm",
        json={"skip_duplicates": True},
        headers=_auth_headers(token),
    )
    assert confirm.status_code == 200, confirm.text
    body = confirm.json()
    assert body["status"] == "completed"
    assert body["stats"]["imported_rows"] == 2
    assert body["stats"]["skipped_rows"] == 0

    balance = await _account_balance(auth_client, token, account_id)
    assert balance == Decimal("1174.5000")

    listed = await auth_client.get(
        f"{TRANSACTIONS_API}?account_id={account_id}&page_size=50",
        headers=_auth_headers(token),
    )
    assert listed.status_code == 200
    assert listed.json()["total_items"] == 2


async def test_upload_rejects_unsupported_content_type(
    auth_client: AsyncClient,
) -> None:
    token = await _register_token(auth_client)
    account_id = await _create_account(auth_client, token)
    csv = CSV_HEADER + "2026-01-15,expense,10.00,Coffee,Groceries,,\n"
    response = await auth_client.post(
        API,
        data={"account_id": account_id},
        files={"file": ("import.csv", BytesIO(csv.encode("utf-8")), "image/png")},
        headers=_auth_headers(token),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_CONTENT_TYPE"


async def test_validation_errors_and_malformed_rows(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    account_id = await _create_account(auth_client, token)
    csv = CSV_HEADER + (
        "2026-01-15,expense,10.00,Ok,Groceries,,\n"
        "bad-date,expense,10.00,Bad,Groceries,,\n"
        "2026-01-17,expense,5.00,Unknown cat,NoSuchCategory,,\n"
    )
    upload = await _upload(auth_client, token, account_id=account_id, content=csv)
    assert upload.status_code == 201, upload.text
    body = upload.json()
    assert body["stats"]["total_rows"] == 3
    assert body["stats"]["valid_rows"] == 1
    assert body["stats"]["invalid_rows"] == 2
    codes = {error["code"] for error in body["errors"]}
    assert "INVALID_TRANSACTION_DATE" in codes
    assert "CATEGORY_NOT_FOUND" in codes

    confirm = await auth_client.post(
        f"{API}/{body['id']}/confirm",
        headers=_auth_headers(token),
    )
    assert confirm.status_code == 200
    assert confirm.json()["stats"]["imported_rows"] == 1
    assert confirm.json()["stats"]["invalid_rows"] == 2


async def test_duplicate_detection_preview_and_skip(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    account_id = await _create_account(auth_client, token)

    # Seed an existing transaction that will fingerprint-match.
    categories = await auth_client.get(
        f"{CATEGORIES_API}?include_system=false&page_size=100",
        headers=_auth_headers(token),
    )
    expense_id = next(
        item["id"]
        for item in categories.json()["items"]
        if item["name"] == "Groceries" and item["category_type"] == "expense"
    )
    seeded = await auth_client.post(
        TRANSACTIONS_API,
        json={
            "account_id": account_id,
            "category_id": expense_id,
            "transaction_type": "expense",
            "amount": "12.5000",
            "description": "Coffee",
            "transaction_date": "2026-01-15",
        },
        headers=_auth_headers(token),
    )
    assert seeded.status_code == 201, seeded.text
    balance_before = await _account_balance(auth_client, token, account_id)

    csv = CSV_HEADER + (
        "2026-01-15,expense,12.50,Coffee,Groceries,,\n"
        "2026-01-15,expense,12.50,Coffee,Groceries,ext-dup,\n"
        "2026-01-15,expense,12.50,Coffee,Groceries,ext-dup,\n"
        "2026-01-20,expense,3.00,Snack,Groceries,ext-new,\n"
    )
    upload = await _upload(auth_client, token, account_id=account_id, content=csv)
    assert upload.status_code == 201, upload.text
    body = upload.json()
    # fingerprint match + second ext-dup (intra-file); first ext-dup is new
    assert body["stats"]["duplicate_rows"] == 2
    assert body["stats"]["valid_rows"] == 2

    confirm = await auth_client.post(
        f"{API}/{body['id']}/confirm",
        json={"skip_duplicates": True},
        headers=_auth_headers(token),
    )
    assert confirm.status_code == 200, confirm.text
    result = confirm.json()
    assert result["stats"]["imported_rows"] == 2
    assert result["stats"]["skipped_rows"] == 2
    assert result["stats"]["duplicate_rows"] == 2

    balance_after = await _account_balance(auth_client, token, account_id)
    assert balance_after == balance_before - Decimal("15.5000")


async def test_file_size_and_type_validation(
    app_settings,
    auth_client: AsyncClient,
) -> None:
    from app.main import create_app

    token = await _register_token(auth_client)
    account_id = await _create_account(auth_client, token)

    # Wrong extension
    bad_type = await _upload(
        auth_client,
        token,
        account_id=account_id,
        content=CSV_HEADER + "2026-01-15,expense,1.00,x,Groceries,,\n",
        filename="data.txt",
    )
    assert bad_type.status_code == 422
    assert bad_type.json()["error"]["code"] == "INVALID_FILE_TYPE"

    # Oversized via dedicated app settings
    small_app = create_app(
        settings=app_settings.model_copy(update={"import_max_file_bytes": 1024}),
    )
    async with small_app.router.lifespan_context(small_app):
        transport = ASGITransport(app=small_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            tok = await _register_token(client, prefix="size")
            acct = await _create_account(client, tok)
            big = CSV_HEADER + ("2026-01-15,expense,1.00,x,Groceries,,\n" * 80)
            assert len(big.encode("utf-8")) > 1024
            response = await _upload(client, tok, account_id=acct, content=big)
            assert response.status_code == 422
            assert response.json()["error"]["code"] == "FILE_TOO_LARGE"


async def test_large_import(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    account_id = await _create_account(
        auth_client,
        token,
        opening_balance="10000.0000",
    )
    rows = [
        f"2026-01-{(i % 28) + 1:02d},expense,1.00,Bulk {i},Groceries,bulk-{i},"
        for i in range(120)
    ]
    csv = CSV_HEADER + "\n".join(rows) + "\n"
    upload = await _upload(auth_client, token, account_id=account_id, content=csv)
    assert upload.status_code == 201, upload.text
    assert upload.json()["stats"]["valid_rows"] == 120
    # Preview is capped
    assert len(upload.json()["preview_rows"]) <= 50

    confirm = await auth_client.post(
        f"{API}/{upload.json()['id']}/confirm",
        headers=_auth_headers(token),
    )
    assert confirm.status_code == 200, confirm.text
    assert confirm.json()["stats"]["imported_rows"] == 120
    balance = await _account_balance(auth_client, token, account_id)
    assert balance == Decimal("9880.0000")


async def test_ownership_isolation(auth_client: AsyncClient) -> None:
    token_a = await _register_token(auth_client, prefix="a")
    token_b = await _register_token(auth_client, prefix="b")
    account_a = await _create_account(auth_client, token_a)
    account_b = await _create_account(auth_client, token_b)

    csv = CSV_HEADER + "2026-01-15,expense,1.00,x,Groceries,,\n"
    upload = await _upload(auth_client, token_a, account_id=account_a, content=csv)
    assert upload.status_code == 201
    job_id = upload.json()["id"]

    # User B cannot see or confirm A's job
    get_b = await auth_client.get(f"{API}/{job_id}", headers=_auth_headers(token_b))
    assert get_b.status_code == 404

    confirm_b = await auth_client.post(
        f"{API}/{job_id}/confirm",
        headers=_auth_headers(token_b),
    )
    assert confirm_b.status_code == 404

    # User A cannot upload into B's account
    cross = await _upload(auth_client, token_a, account_id=account_b, content=csv)
    assert cross.status_code == 404


async def test_confirm_rolls_back_on_failure(
    auth_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = await _register_token(auth_client)
    account_id = await _create_account(auth_client, token)
    csv = CSV_HEADER + (
        "2026-01-15,expense,10.00,One,Groceries,r1,\n"
        "2026-01-16,expense,20.00,Two,Groceries,r2,\n"
        "2026-01-17,expense,30.00,Three,Groceries,r3,\n"
    )
    upload = await _upload(auth_client, token, account_id=account_id, content=csv)
    assert upload.status_code == 201
    job_id = upload.json()["id"]
    balance_before = await _account_balance(auth_client, token, account_id)

    from app.repositories import transaction_repository as txn_repo

    calls = {"n": 0}
    original = txn_repo.create_transaction

    async def flaky_create(*args: object, **kwargs: object) -> object:
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("simulated failure")
        return await original(*args, **kwargs)

    monkeypatch.setattr(
        "app.services.import_service.transaction_repo.create_transaction",
        flaky_create,
    )

    confirm = await auth_client.post(
        f"{API}/{job_id}/confirm",
        headers=_auth_headers(token),
    )
    assert confirm.status_code == 422
    assert confirm.json()["error"]["code"] == "IMPORT_FAILED"

    balance_after = await _account_balance(auth_client, token, account_id)
    assert balance_after == balance_before

    listed = await auth_client.get(
        f"{TRANSACTIONS_API}?account_id={account_id}&page_size=50",
        headers=_auth_headers(token),
    )
    assert listed.json()["total_items"] == 0

    job = await auth_client.get(f"{API}/{job_id}", headers=_auth_headers(token))
    assert job.status_code == 200
    assert job.json()["status"] == "failed"
    assert job.json()["stats"]["imported_rows"] == 0


async def test_list_import_jobs(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    account_id = await _create_account(auth_client, token)
    csv = CSV_HEADER + "2026-01-15,expense,1.00,x,Groceries,,\n"
    first = await _upload(auth_client, token, account_id=account_id, content=csv)
    second = await _upload(auth_client, token, account_id=account_id, content=csv)
    assert first.status_code == 201
    assert second.status_code == 201

    listed = await auth_client.get(API, headers=_auth_headers(token))
    assert listed.status_code == 200
    body = listed.json()
    assert body["total_items"] >= 2
    assert len(body["items"]) >= 2


async def test_confirm_completed_is_idempotent(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    account_id = await _create_account(auth_client, token)
    csv = CSV_HEADER + "2026-01-15,expense,1.00,x,Groceries,,\n"
    upload = await _upload(auth_client, token, account_id=account_id, content=csv)
    job_id = upload.json()["id"]
    first = await auth_client.post(
        f"{API}/{job_id}/confirm",
        headers=_auth_headers(token),
    )
    assert first.status_code == 200
    assert first.json()["status"] == "completed"
    assert first.json()["stats"]["imported_rows"] == 1

    second = await auth_client.post(
        f"{API}/{job_id}/confirm",
        headers=_auth_headers(token),
    )
    assert second.status_code == 200
    assert second.json()["status"] == "completed"
    assert second.json()["stats"]["imported_rows"] == 1

    listed = await auth_client.get(
        f"{TRANSACTIONS_API}?account_id={account_id}&page_size=50",
        headers=_auth_headers(token),
    )
    assert listed.json()["total_items"] == 1


async def test_whitespace_fingerprint_matches_existing(
    auth_client: AsyncClient,
) -> None:
    token = await _register_token(auth_client)
    account_id = await _create_account(auth_client, token)
    categories = await auth_client.get(
        f"{CATEGORIES_API}?include_system=false&page_size=100",
        headers=_auth_headers(token),
    )
    expense_id = next(
        item["id"]
        for item in categories.json()["items"]
        if item["name"] == "Groceries" and item["category_type"] == "expense"
    )
    seeded = await auth_client.post(
        TRANSACTIONS_API,
        json={
            "account_id": account_id,
            "category_id": expense_id,
            "transaction_type": "expense",
            "amount": "12.5000",
            "description": "Coffee Shop",
            "transaction_date": "2026-01-15",
        },
        headers=_auth_headers(token),
    )
    assert seeded.status_code == 201

    csv = CSV_HEADER + "2026-01-15,expense,12.50,Coffee  Shop,Groceries,,\n"
    upload = await _upload(auth_client, token, account_id=account_id, content=csv)
    assert upload.status_code == 201, upload.text
    body = upload.json()
    assert body["stats"]["duplicate_rows"] == 1
    assert body["stats"]["valid_rows"] == 0
    assert body["preview_rows"][0]["is_duplicate"] is True


async def test_confirm_rechecks_live_duplicates(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    account_id = await _create_account(auth_client, token)
    categories = await auth_client.get(
        f"{CATEGORIES_API}?include_system=false&page_size=100",
        headers=_auth_headers(token),
    )
    expense_id = next(
        item["id"]
        for item in categories.json()["items"]
        if item["name"] == "Groceries" and item["category_type"] == "expense"
    )

    csv = CSV_HEADER + "2026-06-01,expense,7.00,Live Dup,Groceries,,\n"
    upload = await _upload(auth_client, token, account_id=account_id, content=csv)
    assert upload.status_code == 201
    assert upload.json()["stats"]["valid_rows"] == 1
    job_id = upload.json()["id"]
    balance_before = await _account_balance(auth_client, token, account_id)

    interleaved = await auth_client.post(
        TRANSACTIONS_API,
        json={
            "account_id": account_id,
            "category_id": expense_id,
            "transaction_type": "expense",
            "amount": "7.0000",
            "description": "Live Dup",
            "transaction_date": "2026-06-01",
        },
        headers=_auth_headers(token),
    )
    assert interleaved.status_code == 201
    balance_after_seed = await _account_balance(auth_client, token, account_id)

    confirm = await auth_client.post(
        f"{API}/{job_id}/confirm",
        json={"skip_duplicates": True},
        headers=_auth_headers(token),
    )
    assert confirm.status_code == 200, confirm.text
    assert confirm.json()["stats"]["imported_rows"] == 0
    assert confirm.json()["stats"]["skipped_rows"] == 1
    assert await _account_balance(auth_client, token, account_id) == balance_after_seed
    assert balance_after_seed == balance_before - Decimal("7.0000")


async def test_confirm_rejects_duplicates_when_skip_disabled(
    auth_client: AsyncClient,
) -> None:
    token = await _register_token(auth_client)
    account_id = await _create_account(auth_client, token)
    categories = await auth_client.get(
        f"{CATEGORIES_API}?include_system=false&page_size=100",
        headers=_auth_headers(token),
    )
    expense_id = next(
        item["id"]
        for item in categories.json()["items"]
        if item["name"] == "Groceries" and item["category_type"] == "expense"
    )

    csv = CSV_HEADER + "2026-06-02,expense,9.00,Reject Dup,Groceries,,\n"
    upload = await auth_client.post(
        API,
        data={"account_id": account_id},
        files={"file": ("dup.csv", BytesIO(csv.encode("utf-8")), "text/csv")},
        headers=_auth_headers(token),
    )
    assert upload.status_code == 201, upload.text
    job_id = upload.json()["id"]

    await auth_client.post(
        TRANSACTIONS_API,
        json={
            "account_id": account_id,
            "category_id": expense_id,
            "transaction_type": "expense",
            "amount": "9.0000",
            "description": "Reject Dup",
            "transaction_date": "2026-06-02",
        },
        headers=_auth_headers(token),
    )

    confirm = await auth_client.post(
        f"{API}/{job_id}/confirm",
        json={"skip_duplicates": False},
        headers=_auth_headers(token),
    )
    assert confirm.status_code == 409
    assert confirm.json()["error"]["code"] == "IMPORT_DUPLICATE_ROW"


async def test_path_traversal_filename_sanitized(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    account_id = await _create_account(auth_client, token)
    csv = CSV_HEADER + "2026-01-15,expense,1.00,x,Groceries,,\n"
    response = await auth_client.post(
        API,
        data={"account_id": account_id},
        files={
            "file": (
                "../etc/passwd.csv",
                BytesIO(csv.encode("utf-8")),
                "text/csv",
            ),
        },
        headers=_auth_headers(token),
    )
    assert response.status_code == 201, response.text
    assert response.json()["original_filename"] == "passwd.csv"
