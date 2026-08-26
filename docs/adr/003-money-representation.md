# ADR 003: Money representation

## Status

Accepted

## Context

Floating-point arithmetic is unsafe for currency.

## Decision

- Represent money with exact decimals (`decimal.Decimal` in Python; PostgreSQL `NUMERIC`).
- Forbid binary floating-point types for monetary storage and calculation.
- Format currency only at presentation boundaries.

## Consequences

- Tests must cover decimal edge cases.
- Analytics and transfers must preserve exact values within a currency.
