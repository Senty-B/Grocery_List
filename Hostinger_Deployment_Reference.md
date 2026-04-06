# Hostinger Deployment Reference (After Build)

> Use this as a quick operational guide when the project is ready to deploy.
>  
> Target: Hostinger VPS (Ubuntu 24.04), Docker, Tailscale, private access.

---

## 1) Conceptual Model (What Happens in Production)

1. Your **source code lives on the server host filesystem**, not inside containers.
2. Docker builds a **web image** from your project files.
3. Docker Compose runs:
   - `web` container (Flask/Gunicorn app)
   - `db` container (PostgreSQL)
4. `web` connects to `db` over Docker network using service hostname `db`.
5. App is published only to host localhost (`127.0.0.1:18080`).
6. Tailscale serves HTTPS access to mobile/remote clients on your tailnet.

Important: containers are replaceable runtime units, not development workspaces.

---

## 2) What You Need on the Server

You need these categories on the VPS:

- **Release code directory** (project files for that release)
- **Shared secrets/config** (`.env.prod`)
- **Persistent data** (Postgres volume + backup folder)
- **Docker + Tailscale runtime**

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

## Step 1: SSH to server

```bash
ssh <user>@100.113.147.56
```

## Step 2: Install/verify runtime dependencies

```bash
docker --version
docker compose version
tailscale status
```

If Docker is missing:

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-v2
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

## Step 3: Place release code on server host

```bash
cd /opt/grocery-app/releases
git clone <your-repo-url> v1.0.0
cd v1.0.0
git checkout v1.0.0
```

## Step 4: Create production env file

```bash
cp .env.prod.example /opt/grocery-app/shared/env/.env.prod
nano /opt/grocery-app/shared/env/.env.prod
```

Set real secrets/passwords.

## Step 5: Build and start containers

```bash
export RELEASE_TAG=v1.0.0
docker build -t grocery-app:${RELEASE_TAG} .
docker compose -f compose.prod.yaml --env-file /opt/grocery-app/shared/env/.env.prod up -d
```

## Step 6: Run DB migrations

Use one migration command style consistently:

```bash
docker compose -f compose.prod.yaml --env-file /opt/grocery-app/shared/env/.env.prod exec web flask db upgrade
# or
docker compose -f compose.prod.yaml --env-file /opt/grocery-app/shared/env/.env.prod exec web alembic upgrade head
```

## Step 7: Verify local app health

```bash
curl -fsS http://127.0.0.1:18080/health || curl -fsS http://127.0.0.1:18080/login >/dev/null
docker compose -f compose.prod.yaml --env-file /opt/grocery-app/shared/env/.env.prod ps
```

## Step 8: Expose via Tailscale HTTPS

```bash
sudo tailscale serve https / http://127.0.0.1:18080
tailscale serve status
```

## Step 9: Validate from mobile client (tailnet-connected)

- Open app URL from Tailscale on phone
- Login/register
- Add/toggle/confirm item
- Validate favorites and shared updates

---

## 7) Upgrade Deployment (New Release)

For each new version:

1. Prepare new folder `/opt/grocery-app/releases/vX.Y.Z`
2. Build new image tag `grocery-app:vX.Y.Z`
3. Take pre-cutover DB backup
4. `docker compose up -d` with new `RELEASE_TAG`
5. Run migrations
6. Run smoke test
7. Keep previous release folder for rollback

---

## 8) Common Mistakes to Avoid

- Cloning/editing code inside running containers
- Publishing web port to `0.0.0.0` when private-only is intended
- Running without DB backups before migration
- Changing env keys without updating app config
- Skipping post-deploy smoke test from phone

---

## 9) Quick Command Set (Copy/Paste)

```bash
cd /opt/grocery-app/releases/v1.0.0
export RELEASE_TAG=v1.0.0
docker build -t grocery-app:${RELEASE_TAG} .
docker compose -f compose.prod.yaml --env-file /opt/grocery-app/shared/env/.env.prod up -d
docker compose -f compose.prod.yaml --env-file /opt/grocery-app/shared/env/.env.prod exec web flask db upgrade
curl -fsS http://127.0.0.1:18080/health || curl -fsS http://127.0.0.1:18080/login >/dev/null
sudo tailscale serve https / http://127.0.0.1:18080
tailscale serve status
```

