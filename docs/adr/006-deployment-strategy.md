# ADR 006: Deployment strategy

## Status

Accepted

## Context

The portfolio deployment target is a single AWS EC2 host with Docker Compose and Nginx.

## Decision

- Package services as Docker images.
- Use Nginx as the public entrypoint.
- Provide `docker-compose.yml` for development and `docker-compose.prod.yml` for production-shaped deploys.
- Configure via environment variables / secrets; never bake secrets into images.

## Consequences

- Local and production topologies stay similar.
- HTTPS and certificate mounting are handled at Nginx in production.
- Migration to RDS later does not require rewriting the application.

See [docs/deployment/](../deployment/) for the full AWS EC2 runbook.
