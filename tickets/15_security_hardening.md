# Ticket 15: Security Hardening & Rate Limiting

**Phase:** 5 — Hardening & Polish  
**Priority:** High  
**Dependencies:** All prior tickets  
**Estimated effort:** Medium

---

## Why This Matters

Even a private app handles passwords and personal data. This ticket adds rate limiting, security headers, and a final validation review.

---

## Tasks

### 1. Add rate limiting

Install `Flask-Limiter`:

Add to `requirements.txt`:
```text
Flask-Limiter>=3.5,<4
```

Add to `app/extensions.py`:
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=[])
```

Initialize in `create_app()`:
```python
limiter.init_app(app)
```

Apply limits in `app/auth/routes.py`:
```python
from app.extensions import limiter

@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def login():
    ...

@auth_bp.route("/register", methods=["GET", "POST"])
@limiter.limit("3 per hour")
def register():
    ...
```

### Rate Limits Reference

| Endpoint | Limit |
|----------|-------|
| POST /login | 5/minute |
| POST /register | 3/hour |
| Other POST | 30/minute |

### 2. Add security headers

Add an `after_request` handler in `create_app()`:

```python
@app.after_request
def set_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response
```

### 3. Review all templates for XSS safety

Jinja2 auto-escapes by default. Verify:
- No use of `{{ ... | safe }}` with user-supplied data
- No `{% autoescape false %}` blocks
- All user input displayed via template variables (not raw HTML)

### 4. Review all validation

Walk through every route that accepts user input and verify:
- Server-side validation is performed (not just client-side)
- Item names are validated with `validate_item_name()`
- Quantities are validated with `validate_quantity()`
- Notes and units are length-checked
- Invite codes are validated

### 5. Review CSRF protection

Verify:
- All POST forms include `{{ form.hidden_tag() }}` or a CSRF token input
- HTMX requests include the CSRF token via the `htmx:configRequest` handler
- `CSRFProtect` is initialized in `extensions.py` and attached to the app

---

## Acceptance Criteria

- [ ] Login endpoint returns `429 Too Many Requests` after 5 failed attempts in one minute
- [ ] Registration endpoint returns `429` after 3 attempts per hour
- [ ] Security headers present on all responses (`X-Content-Type-Options`, `X-Frame-Options`)
- [ ] No `| safe` filter used on user-supplied data in any template
- [ ] All POST routes validate CSRF tokens
- [ ] All user inputs are validated server-side
