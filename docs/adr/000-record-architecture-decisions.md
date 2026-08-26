# ADR 000: Record architecture decisions

## Status

Accepted

## Context

Monetra will make lasting choices about money representation, authentication, persistence, frontend state, and deployment. Those choices must remain discoverable for humans and AI agents.

## Decision

Significant architectural decisions are recorded as Architecture Decision Records under `docs/adr/` using sequential numbering and short descriptive filenames.

## Consequences

- Future agents must read relevant ADRs before changing related subsystems.
- ADRs should describe context, decision, and consequences — not restate the entire specification.
