# Grocery List App - Implementation Roadmap

> **Version:** 1.0 MVP  
> **Status:** Draft for Implementation  
> **Last Updated:** 2026-04-03

This roadmap translates the PDR, Technical Architecture, and Schema specifications into concrete, sequential implementation tickets. Each ticket includes clear dependencies, estimated effort, and acceptance criteria.

Canonical source of truth for routes and HTMX interaction behavior: `Route_Contract.md`.
Canonical source of truth for concurrency-safe duplicate merges: `Concurrency_Duplicate_Merge_Design.md`.

---

## Executive Summary


| Phase       | Focus           | Tickets    |
| ----------- | --------------- | ---------- |
| **Phase 1** | Foundation      | 1-3        |
| **Phase 2** | Core Backend    | 4-8        |
| **Phase 3** | Frontend & UI   | 9-11       |
| **Phase 4** | DevOps & Deploy | 12-14      |
| **Phase 5** | Hardening       | 15-16      |
| **Total**   |                 | 16 tickets |


**Critical Path:** 1 → 2 → 3 → 4 → 5 → 6 → 7 → 9 → 10 → 12 → 15

---

## Phase 1: Foundation

### Ticket 1: Project Structure & App Factory Setup

**Priority:** Critical | **Dependencies:** None

#### Description

Set up the Flask application using the app factory pattern with modular blueprint structure.

#### Tasks

- Create `app/` package with `__init__.py` (app factory)
- Implement `create_app(config_name)` factory function
- Create `config.py` with Config classes (Development, Testing, Production)
- Set up `extensions.py` for lazy-loaded extensions (db, login_manager, csrf)
- Create `wsgi.py` entry point
- Add `requirements.txt` with dependencies
- Set up `.env.example` and `.flaskenv`
- Add structured logging configuration

#### Directory Structure

```
grocery-app/
├── app/
│   ├── __init__.py          # App factory
│   ├── config.py            # Environment configs
│   ├── extensions.py        # Lazy extensions
│   ├── common/              # Shared utilities
│   ├── auth/
│   ├── household/
│   ├── grocery/
│   ├── favorites/
│   ├── templates/
│   └── static/
├── migrations/
├── tests/
├── docker/
├── wsgi.py
├── run.py
└── requirements.txt
```

#### Acceptance Criteria

- `flask run` starts successfully
- App factory creates instances with correct configs
- Environment variables load from `.env`
- All extensions initialize without errors

---

### Ticket 2: Database Setup - PostgreSQL, SQLAlchemy & Alembic

**Priority:** Critical | **Dependencies:** Ticket 1

#### Description

Configure PostgreSQL connection, set up Alembic migrations, and create models for all v1 tables.

#### Tasks

- Configure SQLAlchemy in `extensions.py` and `config.py`
- Initialize Alembic (`alembic init migrations`)
- Configure `alembic.ini` and `migrations/env.py`
- Create models:
  - `Household` (`app/models/household.py`)
  - `User` (`app/models/user.py`)
  - `GroceryItem` (`app/models/grocery_item.py`)
  - `FavoriteItem` (`app/models/favorite_item.py`)
  - `ActivityLog`
- Add `BaseModel` abstract class with timestamps
- Add `normalized_unit` and `normalized_note` to `GroceryItem` model
- Add partial unique index migration for active dedupe key:
  - `(household_id, normalized_name, normalized_unit, normalized_note)` where `status='active'`
- Generate initial migration
- Verify `alembic upgrade head` applies cleanly

#### Model Relationships

```python
# Household
users = db.relationship('User', backref='household', lazy='dynamic')
grocery_items = db.relationship('GroceryItem', backref='household', lazy='dynamic')
favorite_items = db.relationship('FavoriteItem', backref='household', lazy='dynamic')
```

#### Acceptance Criteria

- `alembic upgrade head` creates all tables
- `alembic downgrade -1` removes tables cleanly
- All models have correct relationships
- Database indices created per schema spec
- Active duplicate dedupe index exists and is validated in migration tests

---

### Ticket 3: Common Utilities - Validators, Authz & Exceptions

**Priority:** Critical | **Dependencies:** Ticket 2

#### Description

Build shared utilities for input validation, authorization, and custom exceptions.

#### Tasks

- Create `app/common/exceptions.py`:
  - `AppException` (base)
  - `ValidationError`
  - `AuthorizationError`
  - `NotFoundError`
  - `DuplicateItemError`
- Create `app/common/validators.py`:
  - `normalize_text()` - lowercase, trim, collapse spaces
  - `validate_item_name()` - length, allowed chars
  - `validate_quantity()` - positive numeric
  - `validate_unit()`, `validate_note()`
  - `validate_username()`, `validate_password()`
- Create `app/common/authz.py` with decorators:
  - `require_household()`
  - `require_owner()`
  - `require_active_user()`
- Create `app/common/utils.py`:
  - `generate_invite_code()` - cryptographically secure
  - `log_activity()` - audit logging helper

#### Validation Rules

- Item name: required, max 100 chars, allow unicode, accents, umlauts
- Quantity: positive numeric, default 1.00
- Username: unique, max 50 chars
- Password: min 8 chars

#### Acceptance Criteria

- All validators return appropriate error messages
- `normalize_text()` handles Unicode correctly
- Authorization decorators redirect or return 403
- Unit tests cover edge cases

---

## Phase 2: Core Backend

### Ticket 4: Auth Module - Registration, Login & Household Creation

**Priority:** Critical | **Dependencies:** Ticket 2, 3

#### Description

Complete authentication module with registration, login/logout, password hashing, and session management.

#### Tasks

- Create `app/auth/__init__.py` with blueprint
- Create `app/auth/forms.py` with WTForms:
  - `RegistrationForm`
  - `LoginForm`
  - `JoinHouseholdForm`
- Create `app/auth/services.py`:
  - `register_user()` - creates household + owner user
  - `join_household()` - adds user to existing household
  - `authenticate_user()` - verify credentials
- Create `app/auth/routes.py`:
  - `GET/POST /login`
  - `GET/POST /register`
  - `POST /logout`
  - `POST /household/join`
- Configure Flask-Login with `user_loader`
- Password hashing with bcrypt
- CSRF protection on all forms

#### Routes


| Method   | Endpoint          | Description                       |
| -------- | ----------------- | --------------------------------- |
| GET/POST | `/login`          | Login form                        |
| GET/POST | `/register`       | Registration + household creation |
| POST     | `/logout`         | Logout                            |
| POST     | `/household/join` | Join existing household           |


#### Acceptance Criteria

- User can register and create household
- User can login with valid credentials
- Passwords stored as secure hashes
- Sessions persist correctly
- CSRF tokens validated on POST requests
- Failed logins show appropriate errors

---

### Ticket 5: Grocery Module - Models, Services & Routes

**Priority:** Critical | **Dependencies:** Ticket 4

#### Description

Implement the core grocery list functionality: add items, toggle status, confirm purchase.

#### Tasks

- Create `app/grocery/__init__.py` with blueprint
- Create `app/grocery/services.py`:
  - `add_grocery_item()` - with atomic UPSERT merge
  - `toggle_item_status()` - active ↔ checked
  - `confirm_purchase()` - delete all checked items
  - `get_grocery_list()` - active + checked items
  - `search_items()` - for add-item suggestions
- Create `app/grocery/routes.py`:
  - `GET /grocery` - list page
  - `POST /grocery/items` - add item
  - `POST /grocery/items/<id>/toggle` - toggle status
  - `POST /grocery/confirm` - confirm purchase
  - `GET /grocery/search?q=...` - HTMX search suggestions
- Create `app/grocery/forms.py`:
  - `AddItemForm`
  - `QuickAddForm`
- Implement duplicate merge as a single SQL statement:
  - `INSERT ... ON CONFLICT ... DO UPDATE`
  - Conflict target: active dedupe key from schema

#### HTMX Routes


| Method | Endpoint                     | Response                            |
| ------ | ---------------------------- | ----------------------------------- |
| GET    | `/grocery/search?q=`         | HTML fragment: dropdown suggestions |
| POST   | `/grocery/items`             | Fragment: updated list or redirect  |
| POST   | `/grocery/items/<id>/toggle` | Fragment: updated row               |
| POST   | `/grocery/confirm`           | Fragment: cleared list              |


#### Acceptance Criteria

- Add item with name, quantity, unit, note
- Duplicate items merge quantities
- Concurrent duplicate adds do not create extra active rows
- Toggle active ↔ checked state
- Confirm purchase removes checked items
- Search suggests from favorites and history
- All routes protected by authentication
- Household data isolation enforced

---

### Ticket 6: Favorites Module - Quick-Add & Management

**Priority:** High | **Dependencies:** Ticket 5

#### Description

Implement household-wide favorites for quick-add functionality.

#### Tasks

- Create `app/favorites/__init__.py` with blueprint
- Create `app/favorites/services.py`:
  - `add_favorite()`
  - `remove_favorite()`
  - `reorder_favorites()`
  - `quick_add_from_favorite()`
  - `get_favorites_list()`
- Create `app/favorites/routes.py`:
  - `GET /favorites` - management page
  - `POST /favorites` - add new
- `POST /favorites/<id>/delete` - remove
  - `POST /favorites/<id>/reorder` - change order
  - `POST /favorites/<id>/quick-add` - add to grocery
- Create `app/favorites/forms.py`:
  - `AddFavoriteForm`

#### Routes


| Method | Endpoint                    | Response                             |
| ------ | --------------------------- | ------------------------------------ |
| GET    | `/favorites`                | Full HTML page                       |
| POST   | `/favorites`                | Fragment: updated list               |
| DELETE | `/favorites/<id>`           | 200 OK (remove DOM)                  |
| POST   | `/favorites/<id>/reorder`   | Fragment: reordered list             |
| POST   | `/favorites/<id>/quick-add` | Fragment: feedback + refresh trigger |


#### Acceptance Criteria

- Add item to favorites from grocery list
- Manage favorites page shows all favorites
- Delete favorites
- Reorder favorites
- Quick-add from favorites with default quantity
- First 8 favorites appear on grocery page

---

### Ticket 7: Household Module - Invite Codes & Membership

**Priority:** High | **Dependencies:** Ticket 4

#### Description

Implement household management: invite codes, member limits, role checks.

#### Tasks

- Create `app/household/__init__.py` with blueprint
- Create `app/household/services.py`:
  - `generate_invite_code()` - cryptographically secure
  - `rotate_invite_code()`
  - `get_household_members()`
  - `can_add_member()` - check 5-user limit
- Create `app/household/routes.py`:
  - `GET /household` - household info
  - `POST /household/rotate-code` - new invite code
- Create household dashboard template
- Display invite code for owner
- List current members

#### Routes


| Method | Endpoint                 | Description              |
| ------ | ------------------------ | ------------------------ |
| GET    | `/household`             | Household info page      |
| POST   | `/household/rotate-code` | Generate new invite code |


#### Acceptance Criteria

- Owner can view invite code
- Owner can rotate invite code
- Member limit (5) enforced
- Household members listed
- Role differentiation (owner vs member)

---

### Ticket 8: Testing - Unit & Integration Tests

**Priority:** High | **Dependencies:** Ticket 5, 6, 7

#### Description

Comprehensive test coverage for models, services, and routes.

#### Tasks

- Set up pytest with fixtures
- Create `tests/conftest.py` with:
  - Test database configuration
  - Client fixture
  - Authenticated user fixture
- Unit tests:
  - All validators
  - Duplicate detection logic
  - Item state transitions
  - Favorite ordering
- Integration tests:
  - Registration/login flows
  - Household creation/join
  - Add item flow
  - Toggle item flow
  - Confirm purchase flow
  - Household data isolation
- Configure test database (separate from dev)

#### Test Coverage Targets

- Models: 100%
- Services: 90%+
- Routes: 90%+

#### Acceptance Criteria

- `pytest` runs all tests
- All tests pass
- Tests run in isolated test database
- Coverage report generated

---

## Phase 3: Frontend & UI

### Ticket 9: Tailwind CSS Setup & Base Templates

**Priority:** Critical | **Dependencies:** Ticket 1

#### Description

Set up Tailwind CSS with proper configuration and create base templates.

#### Tasks

- Install Tailwind CSS via CDN or npm
- Configure `tailwind.config.js`
- Create `app/templates/base.html`:
  - Mobile-first viewport
  - Bottom-fixed navigation bar
  - Flash messages area
  - CSRF token inclusion
- Create `app/templates/macros.html`:
  - Form field macros
  - Button macros
  - Alert/flash message macros
- Set up `app/static/css/` with custom styles
- Configure `app/static/js/` for minimal JS

#### Base Template Structure

```html
<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>{% block title %}Grocery List{% endblock %}</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://unpkg.com/htmx.org@1.9.10"></script>
</head>
<body class="bg-gray-50 pb-20">
  {% include '_flash_messages.html' %}
  {% block content %}{% endblock %}
  {% include '_bottom_nav.html' %}
</body>
</html>
```

#### Acceptance Criteria

- Tailwind classes apply correctly
- Base template renders without errors
- Mobile viewport configured
- CSRF token included in all forms

---

### Ticket 10: Grocery List Page - Main UI

**Priority:** Critical | **Dependencies:** Ticket 9

#### Description

Build the main grocery list page with search, active items, checked items, and confirm action.

#### Tasks

- Create `app/templates/grocery/index.html`:
  - Search/add input at top
  - Favorites quick-add row (first 8)
  - Active items list
  - Checked items list (greyed out)
  - Confirm purchase button
- Implement search with HTMX:
  - `hx-get="/grocery/search"`
  - `hx-trigger="keyup changed delay:300ms"`
  - Dropdown suggestions from favorites + history
- Style item rows:
  - Active: clear, prominent
  - Checked: `line-through text-gray-400 bg-gray-50`
- Implement toggle with HTMX:
  - Row click or checkbox
  - `hx-post="/grocery/items/{id}/toggle"`
  - `hx-swap="outerHTML"`
- Implement confirm purchase:
  - Sticky button at bottom
  - Confirmation dialog
  - `hx-post="/grocery/confirm"`

#### UI Components


| Component       | Tailwind Classes                                     |
| --------------- | ---------------------------------------------------- |
| Search input    | `w-full p-4 text-lg border rounded-lg`               |
| Favorite button | `px-3 py-2 bg-blue-100 rounded text-sm`              |
| Active item     | `p-4 border-b flex justify-between bg-white`         |
| Checked item    | `p-4 border-b line-through text-gray-400 bg-gray-50` |
| Confirm button  | `fixed bottom-16 w-full p-4 bg-green-500 text-white` |


#### Acceptance Criteria

- Mobile-first layout works on phone
- Search shows suggestions
- Toggle updates item state
- Confirm removes checked items
- Large touch targets (min 44px)
- Visual distinction between active/checked

---

### Ticket 11: Favorites Page & HTMX Enhancements

**Priority:** High | **Dependencies:** Ticket 10

#### Description

Build favorites management page with HTMX-powered interactions.

#### Tasks

- Create `app/templates/favorites/index.html`:
  - List of favorites with reorder handles
  - Add new favorite form
  - Delete buttons
- Implement reorder with HTMX:
  - Drag handles or up/down buttons
  - `POST /favorites/<id>/reorder`
- Style favorites grid on grocery page:
  - Horizontal scroll or grid
  - Tap to quick-add
- Add HTMX polling (optional):
  - `hx-trigger="every 15s"`
  - `hx-get="/grocery/fragments/list"`

#### Routes


| Method | Endpoint                  | HTMX Attrs                               |
| ------ | ------------------------- | ---------------------------------------- |
| POST   | `/favorites`              | `hx-post`, `hx-target="#favorites-list"` |
| POST   | `/favorites/<id>/delete`  | `hx-post`, `hx-swap="delete"`            |
| POST   | `/favorites/<id>/reorder` | `hx-post`, `hx-swap="outerHTML"`         |


#### Acceptance Criteria

- Favorites page displays all favorites
- Add new favorite works
- Delete removes without page reload
- Reorder changes sort order
- Quick-add from grocery page works
- Polling updates list periodically

---

## Phase 4: DevOps & Deployment

### Ticket 12: Docker & Docker Compose Setup

**Priority:** Critical | **Dependencies:** Ticket 1, 2

#### Description

Containerize the application with Docker and Docker Compose.

#### Tasks

- Create `Dockerfile`:
  - Python 3.12 base image
  - Install dependencies
  - Copy application code
  - Run gunicorn
- Create `docker-compose.yml`:
  - `web` service (Flask app)
  - `db` service (PostgreSQL)
  - Shared volumes for persistence
- Create `docker/Dockerfile` and `docker/docker-compose.yml`
- Configure environment variables in compose
- Add health checks
- Create `.dockerignore`

#### docker-compose.yml

```yaml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - DATABASE_URL=postgresql://...:5432/grocery
      - SECRET_KEY=${SECRET_KEY}
    depends_on:
      - db
    volumes:
      - ./logs:/app/logs
  db:
    image: postgres:16-alpine
    environment:
      - POSTGRES_USER=grocery
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - POSTGRES_DB=grocery
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
volumes:
  postgres_data:
```

#### Acceptance Criteria

- `docker-compose up` starts all services
- Web connects to database
- Migrations run successfully
- App accessible on localhost:5000
- Database persists across restarts

---

### Ticket 13: Production Deployment & SSL

**Priority:** High | **Dependencies:** Ticket 12

#### Description

Set up production deployment with reverse proxy and SSL.
Canonical execution guide for go-live: `Production_Cutover_Runbook.md`.

#### Tasks

- Configure gunicorn for production
  - `gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app`
- Set up Nginx or Caddy reverse proxy:
  - SSL termination
  - Static file serving
  - Security headers
- Configure SSL certificates (Let's Encrypt)
- Create production `.env` template
- Document deployment steps
- Add production security settings:
  - Secure cookies
  - HSTS headers
  - Rate limiting

#### Nginx Config

```nginx
server {
    listen 443 ssl http2;
    server_name grocery.example.com;
    ssl_certificate /etc/letsencrypt/.../fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/.../privkey.pem;
    location / {
        proxy_pass http://web:5000;
        proxy_set_header Host $host;
    }
}
```

#### Acceptance Criteria

- HTTPS works with valid certificate
- HTTP redirects to HTTPS
- Security headers present
- Static files served by nginx
- Production logs visible

---

### Ticket 14: Backup Strategy & Monitoring

**Priority:** Medium | **Dependencies:** Ticket 12

#### Description

Implement database backups and basic monitoring.

#### Tasks

- Create backup script (`scripts/backup.sh`):
  - Daily PostgreSQL dump
  - Compress with gzip
  - Retain 7 days of backups
- Configure cron for automated backups
- Document restore procedure
- Add logging for errors and key events
- Create health check endpoint (`/health`)
- Basic monitoring:
  - Disk space alerts
  - Database connection check

#### Backup Script

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump -h db -U grocery grocery > /backups/grocery_${DATE}.sql
gzip /backups/grocery_${DATE}.sql
find /backups -name "*.gz" -mtime +7 -delete
```

#### Acceptance Criteria

- Daily backups run automatically
- Backups compress successfully
- Old backups cleaned up
- Restore procedure tested once
- Health check endpoint returns 200

---

## Phase 5: Hardening

### Ticket 15: Security Hardening & Input Validation

**Priority:** High | **Dependencies:** All prior

#### Description

Final security pass: input validation, XSS protection, rate limiting.

#### Tasks

- Review all inputs for validation:
  - Item names (max length, allowed chars)
  - Quantities (positive numeric)
  - Notes (max length, no HTML)
- Add server-side rate limiting:
  - Login attempts: 5/minute
  - Registration: 3/hour
  - API endpoints: reasonable limits
- XSS protection:
  - Auto-escape in Jinja2
  - Sanitize any user-displayed content
- Security headers:
  - Content-Security-Policy
  - X-Frame-Options
  - X-Content-Type-Options
- CSRF review: all state-changing forms
- Security audit checklist completed

#### Rate Limits


| Endpoint       | Limit     |
| -------------- | --------- |
| POST /login    | 5/minute  |
| POST /register | 3/hour    |
| Other POST     | 30/minute |


#### Acceptance Criteria

- All inputs validated server-side
- Rate limiting active
- No XSS vulnerabilities (tested)
- Security headers present
- Penetration test passed (basic)

---

### Ticket 16: Documentation & Final Polish

**Priority:** Medium | **Dependencies:** All prior

#### Description

Complete documentation and final UI/UX polish.

#### Tasks

- Write README.md:
  - Project overview
  - Setup instructions
  - Deployment guide
  - Environment variables
- Document API routes (even if internal)
- Create user guide (simple)
- Final UI polish:
  - Loading states
  - Error messages
  - Empty states
- Accessibility check:
  - Labels on all inputs
  - Focus indicators
  - Color contrast
- Performance check:
  - Page load times
  - Database query optimization

#### Documentation Checklist

- README.md complete
- API documentation (routes.md)
- Deployment guide
- User guide (simple)
- Code comments where needed

#### Acceptance Criteria

- New developer can set up in < 30 minutes
- Deployment takes < 15 minutes
- All pages load < 2 seconds
- No console errors
- Accessibility audit passed

---

## Summary

### Critical Path Timeline


| Steps     | Focus |
| -------- | -------- |
| 1. | Foundation: Flask, Database, Common utilities            |
| 2.| Core Backend: Auth, Grocery, Favorites, Household, Tests |
| 3.| Frontend: Tailwind, Main UI, HTMX                        |
| 4. | DevOps: Docker, Deploy, Backups                          |
| 5.| Hardening, Documentation, Polish                         |

### Definition of Done (v1)

- Household creation and member join works
- Grocery items can be added, viewed, checked, confirmed
- Favorites can be managed and used for quick-add
- Concurrent edits don't corrupt data
- Mobile UI is usable in daily life
- Core tests pass
- Migrations are reproducible
- Deployment instructions work

---

## Next Steps

1. **Begin Ticket 1**: Project structure setup
2. **Parallel preparation**: Set up development PostgreSQL instance
3. **Daily sync**: Track progress against this roadmap
4. **Review gate**: After Ticket 8, review before frontend work
5. **Deploy early**: Set up staging after Ticket 12

*This roadmap is a living document. Adjust estimates and priorities as implementation progresses.*