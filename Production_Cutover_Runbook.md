# Production Cutover Runbook (Hostinger + Docker + Tailscale)

> **Status:** v1 production runbook (single source for go-live steps)  
> **Target host:** Hostinger KVM 2 (Ubuntu 24.04)  
> **Tailnet IP:** `100.113.147.56`  
> **App type:** Private household app (Flask + PostgreSQL + HTMX)  
> **Scope:** End-to-end cutover sequence: env, migrations, reverse proxy/TLS, smoke test, rollback

---

## 1) Deployment Decision for This Project

For this v1, use **tailnet-only private deployment** with Docker containers and Tailscale HTTPS proxying.

- App and DB run as containers.
- App is **not exposed on public internet ports**.
- Tailscale provides encrypted access and HTTPS serving to tailnet devices.
- This matches the product scope (private household app) and reduces operational risk.

### Why this is feasible

- Aligns with `Technical Architecture.md` deployment model (Docker + Postgres).
- Keeps attack surface smaller than public internet exposure.
- Still gives phone access: user opens app over Tailscale on mobile.

---

## 2) Target Runtime Topology

- `grocery_web` container (Gunicorn + Flask app), internal port `5000`
- `grocery_db` container (PostgreSQL 16), internal port `5432`
- Docker bridge network: `grocery_net` (isolated from other stacks)
- Docker volumes:
  - `grocery_pg_data` (database persistence)
  - `grocery_logs` (optional persistent app logs)
- Host-level Tailscale reverse proxy:
  - `tailscale serve` forwards HTTPS traffic to `http://127.0.0.1:18080`
  - Host maps `127.0.0.1:18080 -> grocery_web:5000`

Openclaw remains in its own compose project/network and is not changed by this runbook.

---

## 3) Release Prerequisites (Gate Before Cutover)

All items must be true before production deployment:

1. Release commit/tag selected (example: `v1.0.0`).
2. Migration scripts reviewed and reproducible from empty DB.
3. `.env` production values prepared and validated.
4. Backup path exists and write-tested.
5. Health endpoint available (`/health` preferred; fallback `/login`).
6. Tailscale is connected on host (`tailscale status` healthy).

If one item fails, stop cutover.

---

## 4) One-Time Host Setup (Ubuntu 24.04)

Run as a sudo-capable user on `100.113.147.56`.

```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg jq
```

Install Docker Engine + Compose plugin (if not already present):

```bash
sudo apt install -y docker.io docker-compose-v2
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

Log out/in once to refresh group membership.

Verify:

```bash
docker --version
docker compose version
tailscale status
```

---

## 5) Server Directory Layout

```bash
sudo mkdir -p /opt/grocery-app/{releases,shared/{env,backups,logs}}
sudo chown -R "$USER":"$USER" /opt/grocery-app
```

Recommended layout:

- `/opt/grocery-app/releases/<release-tag>/` - checked-out app code
- `/opt/grocery-app/shared/env/.env.prod` - production secrets/config
- `/opt/grocery-app/shared/backups/` - DB backups
- `/opt/grocery-app/shared/logs/` - optional persistent logs

---

## 6) Production Environment File

Create `/opt/grocery-app/shared/env/.env.prod`:

```env
FLASK_ENV=production
SECRET_KEY=<generate-long-random-secret>
DATABASE_URL=postgresql+psycopg://grocery:<db_password>@db:5432/grocery

SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=Lax

LOG_LEVEL=INFO
PASSWORD_HASH_SCHEME=argon2

POSTGRES_DB=grocery
POSTGRES_USER=grocery
POSTGRES_PASSWORD=<db_password>
```

Notes:

- Use long random values for `SECRET_KEY` and DB password.
- Never commit `.env.prod`.
- Cookie secure flag stays `true` because Tailscale serves HTTPS.

---

## 7) Production Compose Baseline

Create `compose.prod.yaml` in each release directory.

```yaml
services:
  web:
    image: grocery-app:${RELEASE_TAG}
    container_name: grocery_web
    env_file:
      - /opt/grocery-app/shared/env/.env.prod
    depends_on:
      db:
        condition: service_healthy
    expose:
      - "5000"
    ports:
      - "127.0.0.1:18080:5000"
    healthcheck:
      test: ["CMD-SHELL", "curl -fsS http://localhost:5000/health || curl -fsS http://localhost:5000/login"]
      interval: 30s
      timeout: 5s
      retries: 5
      start_period: 40s
    restart: unless-stopped
    networks:
      - grocery_net

  db:
    image: postgres:16-alpine
    container_name: grocery_db
    env_file:
      - /opt/grocery-app/shared/env/.env.prod
    volumes:
      - grocery_pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB"]
      interval: 10s
      timeout: 5s
      retries: 10
    restart: unless-stopped
    networks:
      - grocery_net

volumes:
  grocery_pg_data:
  grocery_logs:

networks:
  grocery_net:
    name: grocery_net
```

Important:

- Host bind is `127.0.0.1:18080` only (not public).
- This avoids conflict with Openclaw and avoids accidental internet exposure.

---

## 8) Tailscale HTTPS Reverse Proxy Setup (Host-Level)

Use Tailscale Serve to expose the local app over HTTPS to tailnet devices:

```bash
sudo tailscale serve https / http://127.0.0.1:18080
sudo tailscale serve status
```

This provides:

- reverse proxy behavior,
- TLS termination,
- private tailnet access.

To persist across reboot, ensure the Tailscale service is enabled:

```bash
sudo systemctl enable --now tailscaled
```

---

## 9) Cutover Procedure (Release Day)

### 9.1 Pull release and prepare

```bash
cd /opt/grocery-app/releases
git clone <your-repo-url> v1.0.0
cd v1.0.0
git checkout v1.0.0
```

Build image (or pull if using registry):

```bash
export RELEASE_TAG=v1.0.0
docker build -t grocery-app:${RELEASE_TAG} .
```

### 9.2 Pre-cutover backup (mandatory)

If this is an upgrade (not first deployment), run:

```bash
mkdir -p /opt/grocery-app/shared/backups
docker compose -f compose.prod.yaml --env-file /opt/grocery-app/shared/env/.env.prod exec -T db \
  pg_dump -U grocery -d grocery \
  > /opt/grocery-app/shared/backups/precutover_${RELEASE_TAG}_$(date +%Y%m%d_%H%M%S).sql
gzip /opt/grocery-app/shared/backups/precutover_${RELEASE_TAG}_*.sql
```

### 9.3 Start/upgrade containers

```bash
docker compose -f compose.prod.yaml --env-file /opt/grocery-app/shared/env/.env.prod up -d db
docker compose -f compose.prod.yaml --env-file /opt/grocery-app/shared/env/.env.prod up -d web
```

### 9.4 Run migrations (single authoritative step)

Pick the command used by your implementation and keep it consistent:

```bash
# Option A (Flask-Migrate)
docker compose -f compose.prod.yaml --env-file /opt/grocery-app/shared/env/.env.prod exec web flask db upgrade

# Option B (Alembic direct)
docker compose -f compose.prod.yaml --env-file /opt/grocery-app/shared/env/.env.prod exec web alembic upgrade head
```

### 9.5 Verify health locally on host

```bash
curl -fsS http://127.0.0.1:18080/health || curl -fsS http://127.0.0.1:18080/login >/dev/null
docker compose -f compose.prod.yaml --env-file /opt/grocery-app/shared/env/.env.prod ps
```

### 9.6 Verify over Tailscale

```bash
tailscale serve status
tailscale status --json | jq -r '.Self.DNSName'
```

Open the HTTPS URL from a phone connected to your tailnet and run smoke test.

---

## 10) Post-Cutover Smoke Test (Phone-Focused)

Run in this exact order:

1. Login page loads on phone.
2. Register or login succeeds.
3. Add grocery item with quantity + optional note.
4. Toggle item checked and unchecked.
5. Confirm purchase removes checked items.
6. Add favorite and quick-add from favorite.
7. Second user joins via invite code and sees shared updates.
8. Logout/login cycle works.

If any critical step fails, execute rollback.

---

## 11) Rollback Runbook

Rollback trigger examples:

- Migration failure,
- repeated 5xx after cutover,
- data integrity issue detected in smoke test.

### 11.1 Immediate app rollback (code/container)

```bash
cd /opt/grocery-app/releases/<previous_release>
export RELEASE_TAG=<previous_release>
docker compose -f compose.prod.yaml --env-file /opt/grocery-app/shared/env/.env.prod up -d web
```

### 11.2 Database rollback strategy

Preferred approach for safety:

- restore from pre-cutover SQL backup (do not rely only on down migrations in production).

Example restore:

```bash
gunzip -c /opt/grocery-app/shared/backups/precutover_<bad_release>_<timestamp>.sql.gz > /tmp/restore.sql
docker compose -f compose.prod.yaml --env-file /opt/grocery-app/shared/env/.env.prod exec -T db \
  psql -U grocery -d grocery < /tmp/restore.sql
rm -f /tmp/restore.sql
```

### 11.3 Confirm rollback health

```bash
curl -fsS http://127.0.0.1:18080/health || curl -fsS http://127.0.0.1:18080/login >/dev/null
docker compose -f compose.prod.yaml --env-file /opt/grocery-app/shared/env/.env.prod logs --tail=100 web
```

---

## 12) Operational Schedule (Minimum v1)

- **Daily:** automated DB backup to `/opt/grocery-app/shared/backups`
- **Weekly:** verify one backup file can be decompressed and parsed
- **After each release:** run full smoke test from phone
- **Monthly:** apply Ubuntu package updates + Docker image refresh

---

## 13) Public Internet Exposure (Optional, Not Default for v1)

If you later expose publicly:

- Add Caddy or Nginx reverse proxy container with Let's Encrypt.
- Open only `80/443` in firewall.
- Enforce HTTPS redirect and security headers.
- Keep app bound internally (no direct public `web` port mapping).

This is optional because your current architecture is private-tailnet first.

---

## 14) Production Cutover Checklist (Copy/Paste)

- [ ] Release tag selected and code frozen
- [ ] `.env.prod` validated
- [ ] Pre-cutover backup completed and compressed
- [ ] Containers healthy (`db`, `web`)
- [ ] Migration command executed successfully
- [ ] Local health check passed
- [ ] Tailscale HTTPS route active (`tailscale serve status`)
- [ ] Phone smoke test passed
- [ ] Rollback artifacts verified (previous release + backup)

