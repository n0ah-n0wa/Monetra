# GitHub Actions CI/CD

Monetra uses two GitHub Actions workflows:

| Workflow | File | Purpose |
|----------|------|---------|
| **CI** | `.github/workflows/ci.yml` | Quality gates on pull requests and pushes to `main` |
| **Deploy Production** | `.github/workflows/deploy-production.yml` | Deploy to AWS EC2 after CI passes |

## CI pipeline

Triggered on:

- Pull requests targeting `main` / `master`
- Pushes to `main` / `master`
- Reusable `workflow_call` from the deploy workflow

Jobs (run in parallel unless noted):

| Job | Checks |
|-----|--------|
| `backend-lint` | Ruff check + format |
| `backend-typecheck` | mypy |
| `backend-test` | pytest with PostgreSQL service |
| `frontend-lint` | ESLint + Prettier |
| `frontend-typecheck` | TypeScript |
| `frontend-test` | Vitest |
| `frontend-build` | Production Vite build |
| `docker` | Dev + prod image builds, non-root verification |
| `e2e` | Playwright against local backend + Vite dev server |
| `quality-gate` | Fails the workflow if any job above failed |

Pull requests cannot merge (when branch protection is enabled) until **Quality gate** succeeds.

## Production deployment

Triggered on:

- **Tag push** matching `v*` (e.g. `v1.2.0`)
- **Manual** `workflow_dispatch` with a deploy ref (default `main`)

Flow:

```text
quality (re-runs full CI on the deploy ref)
   ↓
deploy to EC2 over SSH
   ├── git checkout ref on server
   ├── docker compose build
   ├── postgres up + wait
   ├── alembic upgrade head (explicit, fails fast)
   ├── docker compose up -d
   ├── on-host smoke tests
   └── public smoke tests from GitHub runner
```

Deployment uses the GitHub **production** environment so you can require manual approval before promote.

### Required GitHub secrets

Configure in **Settings → Secrets and variables → Actions** (repository or environment scope).

| Secret | Description |
|--------|-------------|
| `EC2_HOST` | Public hostname or Elastic IP of the EC2 instance |
| `EC2_USER` | SSH user (e.g. `monetra`) |
| `EC2_SSH_PRIVATE_KEY` | Private key matching the instance `authorized_keys` |
| `PRODUCTION_URL` | Public HTTPS base URL for smoke tests (e.g. `https://app.example.com`) |

Optional:

| Secret | Default | Description |
|--------|---------|-------------|
| `DEPLOY_PATH` | `/opt/monetra` | Application directory on the EC2 host |

### Secrets that must **not** be in GitHub

Production application secrets (`JWT_SECRET_KEY`, `POSTGRES_PASSWORD`, etc.) belong in `/opt/monetra/.env` on the EC2 host, provisioned once during [initial server setup](./deploy.md). The deploy workflow does **not** write application secrets from GitHub.

Use [AWS Systems Manager Parameter Store](./configuration.md#tier-2--aws-systems-manager-parameter-store) or Secrets Manager if you prefer fetching secrets on the server outside of GitHub.

### GitHub environment setup

1. Create an environment named `production`.
2. Add required reviewers (recommended).
3. Scope the secrets above to the `production` environment when possible.

### Manual deploy

1. Open **Actions → Deploy Production → Run workflow**.
2. Enter the branch, tag, or SHA to deploy.
3. Approve the `production` environment if required.
4. Monitor the job summary; failures include log pointers.

### Tag release deploy

```bash
git tag v1.0.0
git push origin v1.0.0
```

CI runs on the tag, then deploy runs automatically after the quality gate passes.

## Server-side scripts

| Script | Role |
|--------|------|
| `scripts/validate-production-env.sh` | Pre-flight `.env`, TLS, and Compose validation |
| `scripts/deploy-production.sh` | Build, migrate, restart, on-host health/smoke |
| `scripts/smoke-production.sh` | HTTP/HTTPS endpoint verification |
| `scripts/backup-database.sh` | Logical PostgreSQL backup |
| `scripts/rollback-production.sh` | Application code rollback (no schema downgrade) |
| `scripts/prod-clean-deploy-test.sh` | Clean-volume deploy test (Linux/macOS) |
| `scripts/prod-clean-deploy-test.ps1` | Clean-volume deploy test (Windows) |

Run manually on EC2:

```bash
cd /opt/monetra
./scripts/deploy-production.sh v1.0.0
PRODUCTION_URL=https://app.example.com ./scripts/smoke-production.sh "$PRODUCTION_URL"
```

## Failure behaviour

The deploy workflow **fails clearly** when:

- Required GitHub secrets are missing
- CI quality gate fails (deploy job never starts)
- `alembic upgrade head` fails (services are not restarted after migration failure in the script path—postgres may be up; inspect logs)
- Docker health checks do not pass within the timeout
- On-host or public smoke tests return unexpected HTTP status codes

On failure, check:

```bash
ssh monetra@<host> 'cd /opt/monetra && docker compose -f docker-compose.prod.yml ps'
ssh monetra@<host> 'cd /opt/monetra && docker compose -f docker-compose.prod.yml logs --tail=200 backend'
```

## AWS OIDC (optional future enhancement)

The current workflow uses SSH with a deploy key—appropriate for a single EC2 portfolio host. For keyless access, you can later replace SSH with **AWS Systems Manager Session Manager** and an IAM role on the instance; application secrets remain on the server or in AWS secret stores, not in the repository.

## Related documents

- [Deployment overview](./README.md)
- [EC2 host setup](./aws-ec2.md)
- [Configuration and secrets](./configuration.md)
- [Deployment runbook](./deploy.md)
