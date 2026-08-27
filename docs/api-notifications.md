# Notifications API

Base path: `/api/v1/notifications`

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/notifications` | List notifications (`unread_only`, pagination) |
| POST | `/notifications/{id}/read` | Mark one notification as read |
| POST | `/notifications/read-all` | Mark all as read |
| GET | `/notifications/preferences` | Get delivery preferences |
| PATCH | `/notifications/preferences` | Update preferences |

## Event types

- `budget_warning` — budget approaching warning threshold
- `budget_exceeded` — budget over limit
- `recurring_created` — recurring transaction executed
- `goal_milestone` — goal crossed 25/50/75/100%
- `import_completed` / `import_failed`

## Preferences

Per-type in-app toggles plus `email_enabled`. When email is enabled, delivery goes through the abstract `NotificationProvider` (`send_app_notification`) without coupling domain logic to a vendor.

## Ownership

All list/mark/preference operations are scoped to the authenticated user. Cross-user IDs return `404`.
