# Hostinger Deployment Reference (After Build)

> Use this as a quick operational guide when the project is ready to deploy.
>  
> Target: Hostinger VPS (Ubuntu 24.04), Docker, host-based Nginx reverse proxy, HTTPS via Let's Encrypt on a registered domain.

---

## 1) Conceptual Model (What Happens in Production)

1. Your **source code lives on the server host filesystem**, not inside containers.
2. Docker builds a **web image** from your project files.
3. Docker Compose runs:
   - `web` container (Flask/Gunicorn app)
   - `db` container (PostgreSQL)
4. `web` connects to `db` over Docker network using service hostname `db`.
5. App is published only to host localhost (`127.0.0.1:18080`).
6. **Nginx runs on the host** (not in a container) and reverse-proxies HTTPS traffic from `grocery.<your-domain>` to `127.0.0.1:18080`.
7. HTTPS is served with a **trusted Let's Encrypt certificate** issued by Certbot. The cert auto-renews via a systemd timer every 60 days.

Important: containers are replaceable runtime units, not development workspaces.

> **Subdomain pattern:** The grocery app lives on `grocery.<your-domain>`. Future services (e.g. `openclaw.<your-domain>`, `notes.<your-domain>`) get their own subdomain + their own Nginx server block + their own Let's Encrypt cert. The apex (`<your-domain>`) stays free for a landing page or catch-all.

---

## 2) What You Need on the Server

You need these categories on the VPS:

- **Registered domain** with DNS A records for the apex and the `grocery` subdomain pointing at the VPS public IP
- **Release code directory** (project files for that release)
- **Shared secrets/config** (`.env.prod`)
- **Persistent data** (Postgres volume + backup folder)
- **Docker runtime** (containers for web + db)
- **Nginx** (host-based reverse proxy and TLS terminator)
- **Certbot + python3-certbot-nginx** (issues and auto-renews Let's Encrypt certificates)

---

## 3) Server Folder Layout

Recommended host layout:

```text
/opt/grocery-app/
  releases/
    v1.0.0/
      <project files>
  shared/
    env/
      .env.prod
    backups/
    logs/
```

Use this once:

```bash
sudo mkdir -p /opt/grocery-app/{releases,shared/{env,backups,logs}}
sudo chown -R "$USER":"$USER" /opt/grocery-app
```

---

## 4) Repo/File Structure Needed for Deployment

Inside your release folder (`/opt/grocery-app/releases/v1.0.0`), keep at minimum:

```text
<repo-root>/
  app/                         # Flask application package
  migrations/                  # Alembic/Flask-Migrate scripts
  wsgi.py                      # Gunicorn entry point
  requirements.txt             # Python deps
  Dockerfile                   # Web image build recipe
  compose.prod.yaml            # Production service orchestration
  docker/nginx/grocery.conf.example  # Host Nginx site template
  scripts/backup.sh            # Host-run compressed DB backup
  scripts/restore.sh           # Host-run DB restore helper
  .dockerignore                # Build optimization
  Production_Cutover_Runbook.md
```

Also required outside the release folder:

```text
/opt/grocery-app/shared/env/.env.prod
```

---

## 5) “Per Container” File Overview

### `web` container (Flask app)

Needs:

- `Dockerfile` + full app source in release folder
- `compose.prod.yaml`
- `.env.prod` variables (mounted by compose via `env_file`)

Does not need:

- manual code clone inside running container

### `db` container (PostgreSQL)

Needs:

- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` from `.env.prod`
- persistent Docker volume (`grocery_pg_data`)

Does not need:

- project source code inside container

Optional:

- SQL init scripts if you later add DB bootstrap scripts

---

## 6) Step-by-Step Deployment (First Go-Live)

## Step 1: Configure DNS A records

In the Hostinger DNS panel for `<your-domain>`, create (or verify) these records:

| Type | Name       | Value       | TTL  |
|------|------------|-------------|------|
| A    | `@`        | `<VPS_IP>`  | 3600 |
| A    | `grocery`  | `<VPS_IP>`  | 3600 |

Wait a few minutes and verify propagation from your workstation:

```bash
dig grocery.<your-domain> +short    # should return <VPS_IP>
```

Certbot will fail in Step 11 if DNS hasn't propagated — don't continue until `dig` returns the correct IP.

## Step 2: SSH to server

Replace `<VPS_IP>` with your Hostinger VPS public IP.

```bash
ssh <user>@<VPS_IP>
```

## Step 3: Install/verify runtime dependencies

```bash
docker --version
docker compose version
nginx -v
certbot --version
```

If Docker is missing:

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-v2
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

If Nginx or Certbot is missing:

```bash
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx
sudo systemctl enable --now nginx
```

## Step 4: Place release code on server host

```bash
cd /opt/grocery-app/releases
git clone <your-repo-url> v1.0.0
cd v1.0.0
git checkout v1.0.0
```

## Step 5: Create production env file

```bash
cp .env.prod.example /opt/grocery-app/shared/env/.env.prod
nano /opt/grocery-app/shared/env/.env.prod
```

Set real secrets/passwords.

## Step 6: Build and start containers

```bash
export RELEASE_TAG=v1.0.0
docker build -t grocery-app:${RELEASE_TAG} .
docker compose -f compose.prod.yaml --env-file /opt/grocery-app/shared/env/.env.prod up -d
```

## Step 7: Run DB migrations

Use one migration command style consistently:

```bash
docker compose -f compose.prod.yaml --env-file /opt/grocery-app/shared/env/.env.prod exec web flask db upgrade
# or
docker compose -f compose.prod.yaml --env-file /opt/grocery-app/shared/env/.env.prod exec web alembic upgrade head
```

After `upgrade` finishes you should see the latest revision applied, e.g.:

```bash
docker compose -f compose.prod.yaml --env-file /opt/grocery-app/shared/env/.env.prod exec web flask db current
# => 20260423_0004 (head)
```

## Step 8: Bootstrap the first admin account

Public registration has been removed. Every household and user is created by an admin through the admin dashboard, so the very first admin must be created on the server before anyone can log in. This is a **one-time CLI command**; you never run it again unless you want a second admin.

```bash
docker compose -f compose.prod.yaml --env-file /opt/grocery-app/shared/env/.env.prod exec web flask admin create
```

The command will:

- Prompt for a **username** (type it plainly; keep it generic — avoid `admin`, prefer something like `rootadmin` or a real name).
- Prompt for a **password twice**, hidden. Must be **at least 16 characters**. Use a password manager — you will not see it again.
- Print `Admin '<username>' created (id=1).` on success.

Notes worth remembering:

- The admin lives in a separate `admin_user` table and has **no household**. It exists purely to create households and users.
- Admin login URL: `https://grocery.<your-domain>/grocery/admin/login`. It is **not linked** from the public site.
- Any non-admin (including unauthenticated scanners) who hits the admin dashboard gets a `404`, not a `403`, so the endpoint does not advertise itself.
- The account is rate-limited (5 POSTs/min per IP) and locks for 30 minutes after 5 consecutive failed password attempts.
- Re-running `flask admin create` simply adds another admin row. Useful if you want a co-admin as a recovery safety net before you lose your password.

If the command fails with `Admin username is already taken.`, an admin by that name already exists; pick a different username or reset via SQL (see Section 8).

## Step 9: Verify local app health

```bash
curl -fsS http://127.0.0.1:18080/health
docker compose -f compose.prod.yaml --env-file /opt/grocery-app/shared/env/.env.prod ps
```

## Step 10: Open firewall ports and create a minimal Nginx site

Certbot needs HTTP (port 80) open and a server block that answers for `grocery.<your-domain>` in order to run the HTTP-01 challenge.

Open the ports:

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

Create `/etc/nginx/sites-available/grocery` with a temporary HTTP-only block (Certbot will rewrite this in Step 11):

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

## Step 11: Obtain and install the Let's Encrypt certificate

```bash
sudo certbot --nginx -d grocery.<your-domain>
```

When prompted:
- Provide an email for renewal notices.
- Agree to the TOS.
- Choose option **2 (redirect HTTP to HTTPS)** when asked.

Certbot will:
- Prove domain ownership via an HTTP-01 challenge on port 80.
- Issue a cert into `/etc/letsencrypt/live/grocery.<your-domain>/`.
- Rewrite `/etc/nginx/sites-available/grocery` to add a TLS-terminating `listen 443 ssl;` block and an HTTP→HTTPS redirect.
- Install a systemd timer that auto-renews before expiry (every 60 days).

Optionally replace the Certbot-generated file with the cleaner, documented template at `docker/nginx/grocery.conf.example` (adjust `<your-domain>` and keep the same cert paths), then `sudo nginx -t && sudo systemctl reload nginx`.

Verify auto-renewal is configured:

```bash
sudo certbot renew --dry-run
```

## Step 12: Validate end-to-end

From the VPS itself:

```bash
curl -fsS https://grocery.<your-domain>/health   # no -k needed; cert is trusted
```

From any external device (phone on mobile data is ideal):

- Browse to `https://grocery.<your-domain>/login` — no browser warning should appear, and the page must **not** show a "Create account" link.
- Browse to `https://grocery.<your-domain>/grocery/admin/login` and sign in with the admin credentials from Step 8.
- From the admin dashboard, create a household with an owner, then log out.
- Log in as that owner and verify you can add/toggle/confirm an item, and that favorites work.
- Hit `https://grocery.<your-domain>/grocery/admin/` while logged out — it must return a `404`, not a login redirect.

---

## 7) Upgrade Deployment (New Release)

For each new version:

1. Prepare new folder `/opt/grocery-app/releases/vX.Y.Z`
2. Build new image tag `grocery-app:vX.Y.Z`
3. Take pre-cutover DB backup
4. `docker compose up -d` with new `RELEASE_TAG`
5. Run migrations
6. Run smoke test (no need to re-bootstrap the admin — the `admin_user` row persists in the Postgres volume across releases)
7. Update `/opt/grocery-app/releases/current`
8. Keep previous release folder for rollback

Daily backup cron on the host:

```cron
0 3 * * * /opt/grocery-app/releases/current/scripts/backup.sh >> /opt/grocery-app/shared/logs/backup.log 2>&1
```

Manual restore:

```bash
/opt/grocery-app/releases/current/scripts/restore.sh /opt/grocery-app/shared/backups/grocery_<timestamp>.sql.gz
```

---

## 8) Common Mistakes to Avoid

- Cloning/editing code inside running containers
- Publishing web port to `0.0.0.0` (the container must stay on `127.0.0.1:18080`; only Nginx faces the public internet)
- Running without DB backups before migration
- Changing env keys without updating app config
- Skipping post-deploy smoke test from a real device
- Forgetting to open ports 80 and 443 on the firewall
- Running Certbot before DNS has propagated (the HTTP-01 challenge will fail)
- Not verifying auto-renewal works (`sudo certbot renew --dry-run` should return "Congratulations, all renewals succeeded")
- Forgetting to run `flask admin create` after migrations — the site will be reachable but **nobody** can log in, because public registration is disabled
- Picking a weak admin password (the validator requires ≥ 16 characters; use a password manager)
- Losing the admin password with only one admin configured — create a second admin as a recovery safety net, or keep a break-glass reset procedure documented

### Admin password recovery (break-glass)

If you ever lose the admin password and have no second admin, reset it from inside the `web` container. This replaces the stored bcrypt hash with a freshly generated one for the user you name:

```bash
docker compose -f compose.prod.yaml --env-file /opt/grocery-app/shared/env/.env.prod exec web \
  flask shell <<'PY'
from app.auth.services import hash_password
from app.extensions import db
from app.models.admin_user import AdminUser

admin = AdminUser.query.filter_by(username="rootadmin").first()
admin.password_hash = hash_password("the-new-password-at-least-16-chars")
admin.failed_login_count = 0
admin.locked_until = None
db.session.commit()
print("reset ok")
PY
```

Rotate the password again from the UI at your next opportunity and scrub it from shell history.

---

## 9) Quick Command Set (Copy/Paste)

```bash
cd /opt/grocery-app/releases/v1.0.0
export RELEASE_TAG=v1.0.0
docker build -t grocery-app:${RELEASE_TAG} .
docker compose -f compose.prod.yaml --env-file /opt/grocery-app/shared/env/.env.prod up -d
docker compose -f compose.prod.yaml --env-file /opt/grocery-app/shared/env/.env.prod exec web flask db upgrade
docker compose -f compose.prod.yaml --env-file /opt/grocery-app/shared/env/.env.prod exec web flask admin create   # first deploy only
curl -fsS http://127.0.0.1:18080/health
sudo nginx -t && sudo systemctl reload nginx
curl -fsS https://grocery.<your-domain>/health
sudo certbot renew --dry-run
```
