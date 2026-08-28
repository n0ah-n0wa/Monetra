# AWS EC2 host setup

This guide provisions a single EC2 instance suitable for a production-like Monetra deployment using Docker Compose.

## EC2 requirements

### Recommended instance profile

| Attribute | Recommendation | Notes |
|-----------|----------------|-------|
| Instance type | `t3.small` (minimum) or `t3.medium` | 2 vCPU; 2–4 GiB RAM. Increase if import/export workloads are heavy. |
| Architecture | `x86_64` (`amd64`) | Matches published Docker base images in this repository. |
| AMI | Ubuntu 24.04 LTS or Amazon Linux 2023 | Both are supported; examples use Ubuntu. |
| Root volume | 30–50 GiB `gp3` | OS, Docker images, logs, and PostgreSQL data share this disk initially. |
| Elastic IP | **Yes** | Stable public address for DNS and TLS certificate renewal. |
| IAM instance profile | Optional | Attach if using SSM Session Manager or pulling secrets from AWS APIs. |

### Capacity planning

Approximate steady-state footprint on a single host:

| Service | CPU | Memory |
|---------|-----|--------|
| PostgreSQL 16 | low–moderate | 256–512 MiB+ (grows with data) |
| Backend (2 workers) | moderate | 256–512 MiB |
| Frontend (nginx) | low | ~64 MiB |
| Edge nginx | low | ~64 MiB |

Leave headroom for migrations, imports, and OS/Docker overhead. Monitor with `docker stats` after the first week.

### What not to provision (initial deployment)

- **No Kubernetes (EKS)** — operational overhead is not justified for one portfolio instance.
- **No RDS** — optional later; Compose runs PostgreSQL in Docker for the first deployment.
- **No public database port** — PostgreSQL must remain on the internal Docker network only.

## Network and security groups

### Security group rules

Create one security group attached to the EC2 instance.

| Direction | Protocol | Port | Source | Purpose |
|-----------|----------|------|--------|---------|
| Inbound | TCP | 22 | Your admin IP `/32` | SSH (prefer SSM Session Manager and restrict SSH further when possible) |
| Inbound | TCP | 80 | `0.0.0.0/0` | HTTP → HTTPS redirect; Let's Encrypt HTTP-01 if used |
| Inbound | TCP | 443 | `0.0.0.0/0` | HTTPS application traffic |
| Outbound | All | All | `0.0.0.0/0` | Package updates, image pulls, ACME, optional external APIs |

**Do not** expose:

| Port | Service | Reason |
|------|---------|--------|
| 5432 | PostgreSQL | Database must not be reachable from the internet |
| 8000 | Backend API | Access only through Nginx |
| 8080 | Internal frontends | Internal Docker network only |

### Elastic IP

1. Allocate an Elastic IP in the same region as the instance.
2. Associate it with the EC2 instance.
3. Point DNS A/AAAA records to this address (see [deploy.md](./deploy.md#dns)).

## OS setup (Ubuntu 24.04 LTS)

Perform these steps as `root` or with `sudo` on a fresh instance.

### 1. Update the system

```bash
sudo apt-get update
sudo apt-get upgrade -y
sudo reboot
```

Reconnect after reboot.

### 2. Create a deployment user

```bash
sudo adduser --disabled-password --gecos "" monetra
sudo usermod -aG sudo monetra
```

Use this user for application operations. Avoid running Compose as `root`.

### 3. Harden SSH (recommended)

```bash
sudo sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo sed -i 's/^#*PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl reload ssh
```

Install your SSH public key for the `monetra` user before disabling password login.

### 4. Configure automatic security updates

```bash
sudo apt-get install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

Schedule application deployments separately; OS security patches can reboot the host—use a maintenance window or `livepatch` if required.

### 5. Host firewall (UFW)

Defense in depth in addition to the security group:

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status
```

### 6. Set timezone and hostname

```bash
sudo timedatectl set-timezone UTC
sudo hostnamectl set-hostname monetra-prod
```

### 7. Create application directory

```bash
sudo mkdir -p /opt/monetra
sudo chown monetra:monetra /opt/monetra
```

Application code, `.env`, TLS certificates, and backup scripts live under `/opt/monetra`.

## Docker installation

Install the official Docker Engine and Compose plugin (not the deprecated `docker-compose` Python package).

```bash
# Add Docker's official GPG key and repository
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Add the deployment user to the `docker` group:

```bash
sudo usermod -aG docker monetra
```

Log out and back in (or `newgrp docker`) so group membership applies.

Verify:

```bash
docker --version
docker compose version
docker run --rm hello-world
```

### Docker daemon hardening (recommended)

Create `/etc/docker/daemon.json`:

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "live-restore": true
}
```

```bash
sudo systemctl restart docker
```

`live-restore` keeps containers running during daemon restarts (useful during upgrades).

## Optional: AWS Systems Manager

If you prefer not to expose SSH:

1. Attach an IAM role with `AmazonSSMManagedInstanceCore`.
2. Connect with **Session Manager** from the AWS console or CLI.
3. Restrict or remove the SSH security group rule.

## Optional: CloudWatch monitoring

For a portfolio deployment, enable **EC2 detailed monitoring** and consider:

- CloudWatch agent for disk and memory metrics.
- Docker log shipping (future) via CloudWatch Logs.
- An alarm on `StatusCheckFailed` and disk usage > 80%.

These are optional but recommended before calling the environment production.

## Amazon Linux 2023 notes

If using AL2023 instead of Ubuntu:

```bash
sudo dnf update -y
sudo dnf install -y docker
sudo systemctl enable --now docker
sudo usermod -aG docker ec2-user
sudo mkdir -p /usr/local/lib/docker/cli-plugins
sudo curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-$(uname -m) \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
```

Use `firewalld` or security groups only (AL2023 often relies on security groups without a host firewall).

## Next steps

1. [Configure environment variables and secrets](./configuration.md)
2. [Deploy the application](./deploy.md)
