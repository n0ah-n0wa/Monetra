# Financial Goals API

Base path: `/api/v1/goals`

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/goals` | Create a goal |
| GET | `/goals` | List goals (optional `include_progress`, `as_of_date`) |
| GET | `/goals/{id}` | Get one goal |
| GET | `/goals/{id}/progress` | Progress analytics |
| PATCH | `/goals/{id}` | Update |
| POST | `/goals/{id}/archive` | Archive |

## Progress metrics

- `remaining_amount` — capped at zero when target is exceeded
- `completion_percentage` — capped at 100%
- `required_average_contribution` — daily amount needed to reach target by `target_date`
- `average_contribution_rate` — from linked-account transaction history or manual progress timeline
- `projected_completion_date` — based on historical contribution rate
- `target_date_achievable` — whether projection meets `target_date`

All monetary values use exact `Decimal` arithmetic.
