# Monetra production deployment

This directory documents how to deploy Monetra to a **single AWS EC2 instance** using **Docker Compose**. The approach matches [ADR 006](../adr/006-deployment-strategy.md) and `SPECIFICATIONS.md`: Nginx terminates TLS, the API and frontend run in containers, and PostgreSQL runs in Docker on the same host for the initial portfolio deployment.

Kubernetes is **not** required for this topology. A single well-provisioned EC2 host is appropriate for a production-like portfolio deployment with moderate traffic, clear operational boundaries, and low cost.

## Architecture

```text
Internet
   │
   ▼
Route 53 (A/AAAA → Elastic IP)
   │
   ▼
EC2 instance
   ├── Security group: 22 (admin), 80, 443 only
   ├── Docker Engine + Compose plugin
   └── docker-compose.prod.yml
         ├── nginx      (public :80 / :443)
         ├── frontend   (internal)
         ├── backend    (internal, runs Alembic on start)
         └── postgres   (internal volume: postgres_data)
```

## Documentation map

| Document | Contents |
|----------|----------|
| [AWS EC2 host setup](./aws-ec2.md) | Instance sizing, OS hardening, Docker install, security groups, host firewall |
| [Configuration and secrets](./configuration.md) | Environment variables, `.env` layout, secret generation and storage |
| [Deployment runbook](./deploy.md) | DNS, TLS, first deploy, upgrades, migrations, health checks, rollback |
| [Backup and restore](./backup-restore.md) | Scheduled PostgreSQL backups, retention, restore drills, disaster recovery |
| [GitHub Actions CI/CD](./github-actions.md) | CI jobs, production deploy workflow, required secrets |
| [SRE audit](./sre-audit.md) | Production readiness review and failure scenarios |

## Prerequisites

Before deploying:

1. An AWS account with permission to create EC2 instances, security groups, Elastic IPs, and (optionally) Route 53 records.
2. A domain name you control (recommended for HTTPS and cookies).
3. A release artifact: a tagged Git commit or CI-built images.
4. Secrets prepared locally (see [configuration](./configuration.md)); never commit them to Git.

## Quick deploy checklist

Use this after the host is prepared ([aws-ec2.md](./aws-ec2.md)).

```bash
# On the EC2 host
sudo mkdir -p /opt/monetra
sudo chown "$USER":"$USER" /opt/monetra
cd /opt/monetra

git clone <your-repo-url> .
git checkout <release-tag>

cp .env.production.example .env
# Edit .env with production values (secrets, domain, CORS)

# TLS certificates → nginx/certs/fullchain.pem and privkey.pem
# See deploy.md for Let's Encrypt steps

docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

# Verify
curl -f http://127.0.0.1/nginx-health
curl -k -f https://<your-domain>/health
curl -k -f https://<your-domain>/ready
```

A failed `/ready` or container health check means the deployment is **not** successful. Do not route production traffic until all services are healthy.

## Local production-shaped testing

Before touching EC2, validate the same Compose file locally:

```bash
cp .env.production.example .env
./scripts/generate-local-tls-certs.sh   # self-signed certs for local only
./scripts/dev.sh prod-verify
```

## Evolution path

The same application images can later move to:

- **Amazon RDS** for PostgreSQL (change `DATABASE_URL`, remove the `postgres` service from Compose).
- **Application Load Balancer + ACM** for TLS termination (Nginx becomes an internal proxy or is replaced).
- **Separate CI image registry** (ECR) instead of building on the host.

None of these require Kubernetes for a small SaaS footprint.

## Related material

- `docker-compose.prod.yml` — production service definitions
- `.env.production.example` — production environment template
- `docs/architecture.md` — application topology
- `SPECIFICATIONS.md` §§49–51 — deployment, HTTPS, backups
