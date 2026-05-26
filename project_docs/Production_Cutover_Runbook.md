# Production Cutover Runbook (Hostinger + Docker + Nginx)

> **Status:** v1 production runbook (single source for go-live steps)  
> **Target host:** Hostinger KVM 2 (Ubuntu 24.04)  
> **Public IP:** `<VPS_IP>` (replace with your Hostinger VPS public IP)  
> **Domain:** `grocery.<your-domain>` (replace with your registered domain, e.g. subdomain of a Hostinger-managed apex)  
> **App type:** Private household app (Flask + PostgreSQL + HTMX)  
> **Scope:** End-to-end cutover sequence: DNS, env, migrations, reverse proxy/TLS, smoke test, rollback

---

## 1) Deployment Decision for This Project

For this v1, use **host-based Nginx reverse proxy** with Docker containers and a **Let's Encrypt TLS certificate** bound to `grocery.<your-domain>`.

- App and DB run as containers bound to `127.0.0.1:18080` (not publicly exposed).
- **Nginx runs on the host** and reverse-proxies HTTPS traffic from `grocery.<your-domain>` to the web container.
- HTTPS is served with a trusted Let's Encrypt certificate issued by Certbot; the certificate auto-renews every 60 days via a systemd timer.
- Only ports 80 and 443 are open on the public interface; port 5000/18080 stays private.

### Why this is feasible

- Aligns with `Technical Architecture.md` deployment model (Docker + Postgres).
- Let's Encrypt gives us trusted HTTPS with zero cost and zero manual renewal.
- Nginx provides standard reverse-proxy features (TLS termination, forwarded headers, per-subdomain certs).

> **Subdomain pattern:** Future services (e.g. `openclaw.<your-domain>`) get their own Nginx server block + their own Let's Encrypt cert, reusing the same apex domain. The grocery app stays isolated under its own subdomain with its own cookie scope.

---

## 2) Target Runtime Topology

- `grocery_web` container (Gunicorn + Flask app), internal port `5000`
- `grocery_db` container (PostgreSQL 16), internal port `5432`
- Docker bridge network: `grocery_net` (isolated from other stacks)
- Docker volumes:
  - `grocery_pg_data` (database persistence)
  - `grocery_logs` (optional persistent app logs)
- Host-level Nginx reverse proxy:
  - Listens on `:80` (HTTP → HTTPS redirect) and `:443` (TLS termination)
  - Forwards `https://grocery.<your-domain>` traffic to `http://127.0.0.1:18080`
  - Host maps `127.0.0.1:18080 -> grocery_web:5000`
- TLS certificate: Let's Encrypt, stored in `/etc/letsencrypt/live/grocery.<your-domain>/`, auto-renewed by the `certbot.timer` systemd unit

Openclaw remains in its own compose project/network and is not changed by this runbook.

---

## 3) Release Prerequisites (Gate Before Cutover)

All items must be true before production deployment:

1. Release commit/tag selected (example: `v1.0.0`).
2. Migration scripts reviewed and reproducible from empty DB.
3. `.env` production values prepared and validated.
4. Backup path exists and write-tested.
5. Health endpoint available (`/health` preferred; fallback `/login`).
6. Nginx is installed and running on host (`systemctl is-active nginx` returns `active`).
7. Certbot is installed (`certbot --version` succeeds).
8. DNS A record for `grocery.<your-domain>` resolves to the VPS public IP (`dig grocery.<your-domain> +short` returns `<VPS_IP>`).
9. Firewall ports 80 and 443 are open on the public interface.

If one item fails, stop cutover.

---

## 4) One-Time Host Setup (Ubuntu 24.04)

Run as a sudo-capable user on the VPS (SSH via `ssh <user>@<VPS_IP>`).

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

Install Nginx and Certbot:

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
sudo systemctl enable --now nginx
```

Log out/in once to refresh group membership.

Verify:

```bash
docker --version
docker compose version
nginx -v
certbot --version
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
- Cookie secure flag stays `true` because Nginx terminates TLS, and the app enables `ProxyFix` in production so Flask trusts the forwarded HTTPS headers from Nginx.

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
      test: ["CMD-SHELL", "curl -fsS http://localhost:5000/health"]
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

## 8) Nginx Reverse Proxy + Let's Encrypt TLS (Host-Level)

### 8.1 Verify DNS resolves to this VPS

```bash
dig grocery.<your-domain> +short   # must return <VPS_IP>
```

Do not continue if DNS has not propagated — Certbot's HTTP-01 challenge will fail.

### 8.2 Open firewall ports

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

### 8.3 Place a minimal HTTP-only Nginx site for the challenge

Create `/etc/nginx/sites-available/grocery`:

```nginx
server {
    listen 80;
    server_name grocery.<your-domain>;

    location / {
        proxy_pass         http://127.0.0.1:18080;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }
}
```

Enable it:

```bash
sudo ln -sf /etc/nginx/sites-available/grocery /etc/nginx/sites-enabled/grocery
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

### 8.4 Obtain the Let's Encrypt certificate

```bash
sudo certbot --nginx -d grocery.<your-domain>
```

Prompts:
- Email for renewal warnings → provide a real inbox.
- TOS → agree.
- "Redirect HTTP to HTTPS" → choose **option 2 (redirect)**.

Certbot issues the cert, stores it under `/etc/letsencrypt/live/grocery.<your-domain>/`, and rewrites the Nginx site to add a `listen 443 ssl;` block and an HTTP→HTTPS redirect. It also installs the `certbot.timer` systemd unit for auto-renewal.

### 8.5 (Optional) Replace with documented template

If you prefer the cleaner config at `docker/nginx/grocery.conf.example`, copy it over, substitute your domain, and reload:

```bash
sudo cp /opt/grocery-app/releases/v1.0.0/docker/nginx/grocery.conf.example /etc/nginx/sites-available/grocery
sudo sed -i 's/<your-domain>/YOUR_ACTUAL_DOMAIN/g' /etc/nginx/sites-available/grocery
sudo nginx -t && sudo systemctl reload nginx
```

### 8.6 Verify auto-renewal

```bash
sudo certbot renew --dry-run
```

Must end with "Congratulations, all renewals succeeded".

This setup provides:

- reverse proxy behavior (public internet → container),
- TLS termination with a trusted certificate,
- HTTP → HTTPS redirect,
- auto-renewal every 60 days,
- correct forwarded headers so Flask sees the real client IP and protocol.

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
/opt/grocery-app/releases/current/scripts/backup.sh
```

If `/opt/grocery-app/releases/current` is not available yet, run the same script with an explicit compose path:

```bash
COMPOSE_FILE="$(pwd)/compose.prod.yaml" /opt/grocery-app/releases/<release-tag>/scripts/backup.sh
```

The script writes `grocery_<timestamp>.sql.gz` into `/opt/grocery-app/shared/backups` and removes backups older than 7 days.

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
curl -fsS http://127.0.0.1:18080/health
docker compose -f compose.prod.yaml --env-file /opt/grocery-app/shared/env/.env.prod ps
```

### 9.6 Verify HTTPS through Nginx

```bash
sudo nginx -t
sudo systemctl reload nginx
curl -fsS https://grocery.<your-domain>/health     # no -k flag; cert is trusted
```

A successful `200 OK` confirms: Nginx is listening on 443, the Let's Encrypt cert is valid, and the proxy reaches the web container.

Then open `https://grocery.<your-domain>/login` from a phone or laptop on any network and run the smoke test. No browser warning should appear.

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
curl -fsS http://127.0.0.1:18080/health
docker compose -f compose.prod.yaml --env-file /opt/grocery-app/shared/env/.env.prod logs --tail=100 web
```

---

## 12) Operational Schedule (Minimum v1)

- **Daily:** automated DB backup to `/opt/grocery-app/shared/backups`
- **After each release:** run full smoke test from phone
- **Monthly:** apply Ubuntu package updates + Docker image refresh

Create or refresh the active release symlink after a successful deployment:

```bash
ln -sfn /opt/grocery-app/releases/${RELEASE_TAG} /opt/grocery-app/releases/current
```

Install the daily 3 AM host cron job:

```bash
crontab -e
```

Add:

```cron
0 3 * * * /opt/grocery-app/releases/current/scripts/backup.sh >> /opt/grocery-app/shared/logs/backup.log 2>&1
```

Run a manual backup:

```bash
/opt/grocery-app/releases/current/scripts/backup.sh
```

Restore from a backup file:

```bash
/opt/grocery-app/releases/current/scripts/restore.sh /opt/grocery-app/shared/backups/grocery_<timestamp>.sql.gz
```

Weekly backup check:

```bash
gunzip -t /opt/grocery-app/shared/backups/grocery_<timestamp>.sql.gz
```

---

## 13) Adding Future Services Under the Same Domain

Each new service (e.g. a notes app on `notes.<your-domain>`) follows the same pattern — no domain or Nginx re-install required:

1. Add a DNS A record for the new subdomain pointing at `<VPS_IP>`.
2. Run the new service in its own Docker stack, bound to a unique loopback port (e.g. `127.0.0.1:18081`).
3. Create a new Nginx server block in `/etc/nginx/sites-available/<service>` with `server_name <service>.<your-domain>;` and `proxy_pass http://127.0.0.1:18081;`.
4. Issue a cert for it: `sudo certbot --nginx -d <service>.<your-domain>`.
5. Reload Nginx.

Each service gets its own cert, auto-renewed independently. The grocery app's cert, config, and container are untouched.

---

## 14) Production Cutover Checklist (Copy/Paste)

- [ ] Release tag selected and code frozen
- [ ] DNS A record for `grocery.<your-domain>` resolves to `<VPS_IP>` (`dig grocery.<your-domain> +short`)
- [ ] `.env.prod` validated
- [ ] Pre-cutover backup completed and compressed
- [ ] Containers healthy (`db`, `web`)
- [ ] Migration command executed successfully
- [ ] Local container health check passed (`curl http://127.0.0.1:18080/health`)
- [ ] Nginx config test passes (`sudo nginx -t`) and service is reloaded
- [ ] Let's Encrypt cert issued and auto-renewal verified (`sudo certbot renew --dry-run`)
- [ ] Firewall ports 80 and 443 are open
- [ ] External HTTPS access works from a phone at `https://grocery.<your-domain>/login` with no browser warning
- [ ] Phone smoke test passed
- [ ] Rollback artifacts verified (previous release + backup)
