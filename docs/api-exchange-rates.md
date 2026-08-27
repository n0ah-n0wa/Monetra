# Multi-currency & exchange rates

Monetra stores amounts in their original currency and converts for reporting using **dated, stored** exchange rates.

## Rules

- Each account has an immutable base currency after creation.
- Transactions inherit and preserve the account currency (original amount never rewritten by FX).
- Transfers may record an exchange rate for cross-currency moves.
- Users configure `reporting_currency` via `PATCH /api/v1/users/me`.
- Analytics and `/exchange-rates/convert` use stored rates on or before the transaction/as-of date.
- Existing rate snapshots are **not** overwritten unless `overwrite_existing=true` is set explicitly.
- Dashboard/analytics **never** call the live provider per request.

## Provider abstraction (SPEC §23)

| Piece | Role |
|-------|------|
| `ExchangeRateProvider` | Swappable interface returning timestamped `ProviderRateQuote` |
| `StaticExchangeRateProvider` | Configurable rates (no network / no credentials) |
| `InMemoryExchangeRateProvider` | Deterministic test provider |
| `CachingExchangeRateProvider` | TTL cache + optional stale fallback on failure |
| `UnavailableExchangeRateProvider` | Safe default when no provider is configured |

A future HTTP/vendor provider can implement the same interface without changing analytics.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/exchange-rates` | Store a dated rate snapshot |
| GET | `/api/v1/exchange-rates` | List stored rates (paginated) |
| GET | `/api/v1/exchange-rates/lookup` | Lookup rate on/before a date (`exact=true` for exact date) |
| POST | `/api/v1/exchange-rates/convert` | Convert using stored historical rates only |
| POST | `/api/v1/exchange-rates/fetch` | Fetch from configured provider and store |
| PATCH | `/api/v1/users/me` | Update `reporting_currency` |

## Provider configuration

| Env | Values |
|-----|--------|
| `EXCHANGE_RATE_PROVIDER` | `none` (default), `static`, or `test` |
| `EXCHANGE_RATE_STATIC_RATES` | `EUR:USD:1.1,GBP:USD:1.25` when provider is `static` |
| `EXCHANGE_RATE_CACHE_TTL_SECONDS` | Cache TTL (default `300`; `0` disables) |
| `EXCHANGE_RATE_ALLOW_STALE_ON_FAILURE` | Use stale cache on provider failure (default `true`) |

No external API credentials are required or hardcoded for built-in providers.

## Example

```http
POST /api/v1/exchange-rates
Authorization: Bearer <token>
Content-Type: application/json

{
  "base_currency": "EUR",
  "quote_currency": "USD",
  "rate": "1.10000000",
  "rate_date": "2026-01-15",
  "source": "manual"
}
```
