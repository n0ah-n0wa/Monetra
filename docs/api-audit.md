# Audit Events API

Base path: `/api/v1/audit-events`

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/audit-events` | List audit events for the authenticated actor |

Optional filter: `entity_type` (`transaction`, `transfer`, `financial_account`, `budget`, `import_job`).

## Recorded operations

- Transaction create / update / soft-delete
- Transfer create
- Account archive
- Budget create / update / archive
- Import execution (successful confirm)

## Payload

Each event includes actor, action, entity type, entity ID, timestamp, and sanitized metadata. Passwords, tokens, secrets, and related authentication material are never stored.
