# Ticket 13: Production Deployment Configuration

**Phase:** 4 — DevOps & Deployment  
**Priority:** High  
**Dependencies:** Ticket 12  
**Estimated effort:** Medium

---

## Why This Matters

This ticket prepares everything needed for production deployment on the Hostinger VPS with Tailscale private access.

## Reference

- `Production_Cutover_Runbook.md` (full document — the canonical go-live guide)
- `Hostinger_Deployment_Reference.md` (operational quick reference)
- `.env.prod.example` (already in repo)

---

## Tasks

### 1. Verify `.env.prod.example` is complete

The file should contain all environment variables the app needs. Compare against `app/config.py` and the Production Cutover Runbook section 6. The existing `.env.prod.example` looks correct.

### 2. Configure Gunicorn for production

The `Dockerfile` CMD already uses Gunicorn. Verify settings:

- `--workers 2` (sufficient for 2–5 users)
- `--bind 0.0.0.0:5000` (container-internal, host binding is handled by compose)
- `--timeout 120` (generous timeout for slow operations)

### 3. Ensure migration command works in container

Test this command:

```bash
docker compose -f compose.prod.yaml --env-file /opt/grocery-app/shared/env/.env.prod exec web flask db upgrade
```

### 4. Add production security settings to `app/config.py`

Ensure `ProductionConfig` reads all cookie/security settings from environment:

```python
class ProductionConfig(BaseConfig):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "true").lower() == "true"
    SESSION_COOKIE_HTTPONLY = os.environ.get("SESSION_COOKIE_HTTPONLY", "true").lower() == "true"
    SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
```

### 5. Document the deployment steps

Ensure the Production Cutover Runbook is accurate and can be followed step by step. The file already exists — review it and fix any references that don't match the actual code structure.

---

## Acceptance Criteria

- [ ] `.env.prod.example` contains all required env vars
- [ ] Building the Docker image succeeds: `docker build -t grocery-app:v1.0.0 .`
- [ ] Production compose starts and health checks pass
- [ ] Migration runs successfully in the production container
- [ ] Secure cookies are enabled when `SESSION_COOKIE_SECURE=true`
- [ ] Production Cutover Runbook matches actual file structure and commands
