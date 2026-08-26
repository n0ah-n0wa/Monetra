# Accounts and Categories API

Authenticated endpoints under `/api/v1`. All require `Authorization: Bearer <access_token>`.

## Accounts

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/accounts` | Create account |
| `GET` | `/accounts` | List accounts (paginated) |
| `GET` | `/accounts/{id}` | Retrieve account |
| `PATCH` | `/accounts/{id}` | Update name or type |
| `POST` | `/accounts/{id}/archive` | Archive account |

Accounts are never physically deleted. Archived accounts remain queryable for historical reporting.

### Create account body

```json
{
  "name": "Checking",
  "account_type": "bank",
  "currency": "USD",
  "opening_balance": "1000.0000"
}
```

Supported `account_type` values: `cash`, `bank`, `savings`, `credit_card`, `digital_wallet`.

### List query parameters

- `page` (default `1`)
- `page_size` (default `20`, max `100`)
- `status` — optional filter: `active` or `archived`

## Categories

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/categories` | Create user category |
| `GET` | `/categories` | List categories (paginated) |
| `PATCH` | `/categories/{id}` | Update user category |
| `POST` | `/categories/{id}/archive` | Archive user category |

System categories are read-only. User categories are never physically deleted.

New users receive default income and expense categories at registration.

### Create category body

```json
{
  "name": "Side Projects",
  "category_type": "income",
  "icon": "briefcase",
  "color": "#336699"
}
```

User-created categories must be `income` or `expense` type.

### List query parameters

- `page`, `page_size` — same as accounts
- `status` — optional: `active` or `archived`
- `category_type` — optional: `income`, `expense`, or `universal`
- `include_system` (default `true`) — include system categories in results

## Ownership

All operations are scoped to the authenticated user. Accessing another user's resource ID returns `404` with code such as `ACCOUNT_NOT_FOUND` or `CATEGORY_NOT_FOUND`.

## Errors

| Code | HTTP | Meaning |
|------|------|---------|
| `ACCOUNT_NAME_CONFLICT` | 409 | Duplicate account name for user |
| `CATEGORY_NAME_CONFLICT` | 409 | Duplicate category name/type for user |
| `ACCOUNT_ARCHIVED` | 422 | Cannot modify archived account |
| `CATEGORY_ARCHIVED` | 422 | Cannot modify archived category |
| `INVALID_CURRENCY` | 422 | Invalid currency code |
| `INVALID_CATEGORY_TYPE` | 422 | User category must be income or expense |
