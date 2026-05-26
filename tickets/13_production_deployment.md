# Ticket 13: Production Deployment Configuration

**Phase:** 4 — DevOps & Deployment  
**Priority:** High  
**Dependencies:** Ticket 12  
**Estimated effort:** Medium

---

## Why This Matters

This ticket prepares everything needed for production deployment on the Hostinger VPS.

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

### 5. Configure host-based Nginx reverse proxy with Let's Encrypt TLS

Remote access is provided by **Nginx on the VPS host** (not in a container), reverse-proxying HTTPS traffic from `grocery.<your-domain>` to the web container on `127.0.0.1:18080`. See `Hostinger_Deployment_Reference.md` section 6, steps 1 + 9–11 for full commands.

Summary:

- Register the domain and add a DNS **A record** for `grocery.<your-domain>` pointing at the VPS public IP. Verify with `dig grocery.<your-domain> +short`.
- Install Nginx and Certbot on the VPS host (`sudo apt install -y nginx certbot python3-certbot-nginx`).
- Open firewall ports 80 and 443.
- Create an initial HTTP-only server block in `/etc/nginx/sites-available/grocery` with `server_name grocery.<your-domain>;` and a `proxy_pass` to `http://127.0.0.1:18080` (needed for Certbot's HTTP-01 challenge).
- Enable the site, remove the default site, run `sudo nginx -t`, then `sudo systemctl reload nginx`.
- Run `sudo certbot --nginx -d grocery.<your-domain>` — this issues a trusted cert, rewrites the Nginx config to add the HTTPS `listen 443 ssl;` block and an HTTP→HTTPS redirect, and installs a systemd timer that auto-renews the cert every 60 days.
- Optionally replace the Certbot-generated file with the cleaner, documented template at `docker/nginx/grocery.conf.example` (substitute `<your-domain>`), then reload Nginx.
- Confirm auto-renewal with `sudo certbot renew --dry-run`.

Do **not** expose port 5000 or 18080 directly on the public interface — the web container stays bound to `127.0.0.1:18080` and only Nginx faces the internet.

> **Subdomain pattern:** Future services reuse the same apex by adding a DNS record, a new Nginx server block, and their own Certbot cert — the grocery stack is untouched.

### 6. Document the deployment steps

Ensure the Production Cutover Runbook is accurate and can be followed step by step. The file already exists — review it and fix any references that don't match the actual code structure.

---

## Acceptance Criteria

- [ ] `.env.prod.example` contains all required env vars
- [ ] Building the Docker image succeeds: `docker build -t grocery-app:v1.0.0 .`
- [ ] Production compose starts and health checks pass
- [ ] Migration runs successfully in the production container
- [ ] Secure cookies are enabled when `SESSION_COOKIE_SECURE=true`
- [ ] DNS A record for `grocery.<your-domain>` resolves to the VPS public IP
- [ ] Nginx reverse proxy is installed on the host and forwards HTTPS traffic for `grocery.<your-domain>` to `127.0.0.1:18080`
- [ ] Let's Encrypt certificate is issued and loaded from `/etc/letsencrypt/live/grocery.<your-domain>/`
- [ ] `curl -fsS https://grocery.<your-domain>/health` returns `200 OK` from the VPS itself (no `-k` flag needed)
- [ ] `sudo certbot renew --dry-run` finishes with "Congratulations, all renewals succeeded"
- [ ] App is reachable over HTTPS at `https://grocery.<your-domain>/login` from an external device with no browser warning
- [ ] Web container is NOT exposed on the public interface (only `127.0.0.1:18080`)
- [ ] Production Cutover Runbook matches actual file structure and commands
