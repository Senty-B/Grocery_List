# Ticket 12: Docker & Docker Compose Setup

**Phase:** 4 — DevOps & Deployment  
**Priority:** Critical  
**Dependencies:** Ticket 1, Ticket 2  
**Estimated effort:** Small–Medium

---

## Why This Matters

Docker packages the app and database into containers that run the same way everywhere — your laptop, a VPS, or a Raspberry Pi. Docker Compose orchestrates both containers together.

## Reference

- `compose.prod.yaml` (already in repo)
- `Hostinger_Deployment_Reference.md` sections 1–5

---

## Tasks

### 1. Create the Dockerfile

`Dockerfile` (at project root):

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "wsgi:app"]
```

**What each line does:**
- `FROM python:3.12-slim` — start with a minimal Python image.
- `WORKDIR /app` — set the working directory inside the container.
- `COPY requirements.txt .` then `RUN pip install` — install Python dependencies first (Docker caches this layer).
- `COPY . .` — copy the rest of the code.
- `CMD` — the command that runs when the container starts. Gunicorn is a production-grade Python web server.

### 2. Create `.dockerignore`

```text
__pycache__
*.pyc
.env
.env.prod
.git
.gitignore
*.md
tests/
.venv/
node_modules/
```

### 3. Create `docker-compose.yml` for local development

```yaml
services:
  web:
    build: .
    container_name: grocery_web_dev
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=development
      - SECRET_KEY=dev-secret-change-me
      - DATABASE_URL=postgresql+psycopg://grocery:grocery@db:5432/grocery_dev
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - .:/app
    command: flask run --host=0.0.0.0 --debug

  db:
    image: postgres:16-alpine
    container_name: grocery_db_dev
    environment:
      - POSTGRES_USER=grocery
      - POSTGRES_PASSWORD=grocery
      - POSTGRES_DB=grocery_dev
    ports:
      - "5432:5432"
    volumes:
      - dev_pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U grocery -d grocery_dev"]
      interval: 5s
      timeout: 3s
      retries: 10

volumes:
  dev_pg_data:
```

### 4. Verify the production compose file

The file `compose.prod.yaml` already exists in the repo. Verify it matches the spec from `Production_Cutover_Runbook.md` section 7. Key points:

- Web binds to `127.0.0.1:18080` only (not `0.0.0.0`)
- Uses `env_file` pointing to `/opt/grocery-app/shared/env/.env.prod`
- Both services on `grocery_net` network
- Health checks present on both services

### 5. Add a health check endpoint

In `app/__init__.py`, add inside `create_app()`:

```python
@app.route("/health")
def health():
    return "OK", 200
```

### 6. Test the full stack locally

```bash
docker compose up --build
# In another terminal:
docker compose exec web flask db upgrade
# Open http://localhost:5000/login
```

---

## Acceptance Criteria

- [ ] `docker compose up --build` starts both web and db containers
- [ ] Web container connects to the database
- [ ] `flask db upgrade` runs successfully inside the web container
- [ ] App is accessible at `http://localhost:5000`
- [ ] `/health` returns `200 OK`
- [ ] Database data persists after `docker compose down && docker compose up`
- [ ] Production compose file binds to `127.0.0.1:18080` only
