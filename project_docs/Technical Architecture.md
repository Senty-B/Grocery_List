# Shared Household Grocery App

| | |
|---|---|
| **Version** | 1.0 |
| **Status** | Draft for architecture baseline |
| **System Type** | Private, small-scope, mobile-first web application |

*Implements the scope defined in [[PDR Shared Household Grocery App]].*

---

### 1. Purpose

This document defines the target technical architecture for a small private web application used by a household of up to five active users to manage a shared grocery list.

It translates the approved product scope into an engineering design that favors:

- simplicity
- maintainability
- modularity
- reliability
- low operational overhead

This specification covers the v1 system only.

---

### 2. System Goals

#### 2.1 Primary technical goals

- Deliver a stable shared grocery list for 2–5 active users
- Keep architecture as simple as possible while remaining robust
- Support safe concurrent updates from multiple clients
- Be straightforward to deploy and maintain by one developer
- Use clear module boundaries to support future extension

#### 2.2 Secondary technical goals

- Make v2 features possible without major redesign
- Keep dependencies limited and justified
- Minimize operational complexity
- Ensure predictable data consistency

#### 2.3 Explicit non-goals

- No microservices
- No event-driven distributed architecture
- No WebSocket-based real-time sync in v1
- No public API platform
- No offline-first architecture
- No horizontal scaling design for large user counts

---

### 3. Architecture Overview

The system will be implemented as a modular monolith with a server-rendered web UI, backed by PostgreSQL.

#### 3.1 Chosen architecture

| Layer | Choice |
|-------|--------|
| Frontend | Server-rendered HTML templates with Tailwind CSS and small JavaScript enhancements |
| Interaction model | HTMX-enhanced partial page updates for responsive UX without SPA complexity |
| Backend | Flask application organized into domain-oriented modules |
| Database | PostgreSQL as the single persistent source of truth |
| Deployment | Docker Compose with separate app and database services |

#### 3.2 Rationale

- This architecture is the best fit for the actual problem:
  - the user base is extremely small
  - the domain is simple
  - reliability matters more than sophistication
  - server-rendering avoids unnecessary frontend complexity
  - PostgreSQL provides stronger concurrency guarantees and cleaner long-term maintenance than SQLite
  - a modular monolith provides clean separation without the cost of distributed systems

---

### 4. High-Level System Context

#### 4.1 Actors

- Household owner
- Household member
- Browser client on smartphone
- Application server
- PostgreSQL database

#### 4.2 Core interaction pattern

1. User opens the grocery page in a mobile browser
2. Browser loads server-rendered HTML
3. User performs actions such as add, toggle, or confirm
4. Browser submits form or HTMX request to backend
5. Backend validates input and performs transactional database write
6. Backend returns updated HTML fragment or redirect response
7. Browser displays the updated shared state

---

### 5. Architectural Principles

#### 5.1 Simplicity first

- Use the least complex solution that still provides correct behavior.

#### 5.2 Server-side source of truth

- All critical validation, state transitions, and permissions are enforced on the server.

#### 5.3 Modular boundaries

- Code should be organized by domain, not by framework artifact alone.

#### 5.4 Strong consistency over eventual sophistication

- For a household list, consistency and predictability are more valuable than advanced async patterns.

#### 5.5 Progressive enhancement

- The app should work with standard form submissions and become smoother via HTMX/JS enhancements.

#### 5.6 Future extensibility without speculative engineering

- Design for likely future additions such as meal planning and notes, but do not build their infrastructure yet.

---

### 6. Technology Stack

| Area | Technology | Rationale |
|------|------------|-----------|
| **6.1 Frontend** | HTML5, Jinja2 templates, Tailwind CSS, HTMX, minimal vanilla JavaScript | This provides a responsive mobile UI without the complexity of React/Vue build systems, client-side state management, or API-heavy frontend logic. |
| **6.2 Backend** | Python 3.12+, Flask, Flask-Login, SQLAlchemy, Alembic, WTForms or schema-based server validation layer, CSRF protection via Flask-WTF or equivalent | Flask is sufficient for the domain and keeps the implementation lightweight. SQLAlchemy and Alembic provide maintainable persistence and migrations. |
| **6.3 Database** | PostgreSQL 16+ | PostgreSQL supports transactional integrity, safe concurrent writes, mature indexing, and long-term maintainability. |
| **6.4 Deployment / runtime** | Docker, Docker Compose, Gunicorn, host-based Nginx reverse proxy with Let's Encrypt (via Certbot) for TLS | Nginx runs on the VPS host (not in a container) and terminates HTTPS for `grocery.<your-domain>`, proxying to the web container bound to `127.0.0.1:18080`. |

---

### 7. Application Structure

The application will follow a modular monolith structure with an app factory and domain-specific blueprints.

#### 7.1 Proposed package structure

```
app/
  __init__.py
  config.py
  extensions.py

  auth/
    routes.py
    forms.py
    services.py
    models.py

  household/
    routes.py
    forms.py
    services.py
    models.py

  grocery/
    routes.py
    forms.py
    services.py
    models.py

  favorites/
    routes.py
    forms.py
    services.py
    models.py

  common/
    authz.py
    validators.py
    exceptions.py
    utils.py

  templates/
  static/

migrations/
tests/
docker/
```

#### 7.2 Module responsibilities

| Module | Responsibilities |
|--------|------------------|
| **auth** | registration; login/logout; password hashing/verification; session handling |
| **household** | create household; join household via invite code; membership checks; owner/member role rules |
| **grocery** | grocery list display; add item; merge duplicate items; toggle checked state; confirm purchase; list query and sorting behavior |
| **favorites** | create favorite; remove favorite; reorder favorite; quick-add favorite item |
| **common** | shared validation helpers; permission decorators; exception handling; reusable utilities |

---

### 8. Data Architecture

#### 8.1 Data model overview

The system is centered on the **Household** entity. All user, grocery, and favorite records are scoped to a household.

**Core entities**

- Household
- User
- GroceryItem
- FavoriteItem
- Optional ActivityLog

#### 8.2 Entity definitions

##### Household

Represents one private shared environment.

**Key fields**

| Field |
|-------|
| id |
| name |
| invite_code |
| created_at |

**Constraints**

- invite code unique
- one household contains up to five active users

##### User

Represents an authenticated member of a household.

**Key fields**

| Field |
|-------|
| id |
| household_id |
| username |
| password_hash |
| role |
| is_active |
| created_at |

**Constraints**

- username unique within system or within household, depending on chosen policy
- role limited to owner or member

##### GroceryItem

Represents an active or checked item on the shared list.

**Key fields**

| Field |
|-------|
| id |
| household_id |
| name |
| normalized_name |
| quantity_value |
| unit |
| note |
| status |
| checked_by_user_id |
| checked_at |
| created_by_user_id |
| created_at |
| updated_at |

**Constraints**

- status limited to active or checked
- quantity_value > 0
- normalized fields used for duplicate merge logic

##### FavoriteItem

Represents a reusable household-wide quick-add template.

**Key fields**

| Field |
|-------|
| id |
| household_id |
| name |
| normalized_name |
| default_quantity_value |
| default_unit |
| default_note |
| sort_order |
| created_at |
| updated_at |

**Constraints**

- order integer required
- favorites household-scoped

##### ActivityLog (recommended)

Represents domain-relevant audit events.

**Key fields**

| Field |
|-------|
| id |
| household_id |
| user_id |
| action_type |
| entity_type |
| entity_id |
| payload_json |
| created_at |

**Use**

- debugging
- light traceability
- operational support

#### 8.3 Relational model

- A household has many users
- A household has many grocery items
- A household has many favorites
- A user may create many grocery items
- A user may check many grocery items
- A user may produce many activity log entries

#### 8.4 Indexing strategy

**Required indexes**

| Index target |
|--------------|
| household.invite_code |
| user.household_id |
| grocery_item.household_id |
| grocery_item.household_id + status |
| grocery_item.household_id + normalized_name |
| UNIQUE partial index on grocery_item `(household_id, normalized_name, normalized_unit, normalized_note)` where status is active |
| favorite_item.household_id + sort_order |
| favorite_item.household_id + normalized_name |

**Optional indexes**

| Index target |
|--------------|
| activity_log.household_id + created_at |

#### 8.5 Duplicate item handling

Canonical implementation details: `Concurrency_Duplicate_Merge_Design.md`.

Duplicate management is DB-enforced and write-path atomic.

**Definition of duplicate**

| Criterion |
|-----------|
| same household |
| same normalized name |
| same normalized unit |
| same normalized note |
| existing item status is active |

**Behavior**

- add-item uses one `INSERT ... ON CONFLICT ... DO UPDATE` statement
- conflict target is the active-item dedupe key: household + normalized name + normalized unit + normalized note
- if duplicate exists, quantity is incremented
- if no duplicate exists, a new active row is inserted

This keeps the visible list cleaner while remaining predictable.

---

### 9. State Model

#### 9.1 Grocery item states

Two states only:

- active
- checked

#### 9.2 State transitions

| Transition | Result |
|------------|--------|
| add item | → active |
| toggle active | → checked |
| toggle checked | → active |
| confirm purchase | checked items are deleted |

#### 9.3 Rationale

A two-state model keeps the workflow understandable and sufficient for the domain.

---

### 10. Request/Response Architecture

The app uses standard HTTP requests with HTML responses and partial updates.

#### 10.1 Interaction pattern

- full-page GET requests for page loads
- POST requests for state-changing actions
- HTMX partial responses for in-page updates when useful

#### 10.2 Route strategy

Canonical source of truth: `Route_Contract.md`.

| Area | Method | Path |
|------|--------|------|
| Authentication | GET | `/login` |
| Authentication | POST | `/login` |
| Authentication | POST | `/logout` |
| Authentication | GET | `/register` |
| Authentication | POST | `/register` |
| Household | GET | `/household/setup` |
| Household | POST | `/household/create` |
| Household | POST | `/household/join` |
| Grocery | GET | `/grocery` |
| Grocery | POST | `/grocery/items` |
| Grocery | POST | `/grocery/items/<id>/toggle` |
| Grocery | POST | `/grocery/confirm` |
| Favorites | GET | `/favorites` |
| Favorites | POST | `/favorites` |
| Favorites | POST | `/favorites/<id>/delete` |
| Favorites | POST | `/favorites/<id>/reorder` |
| Favorites | POST | `/favorites/<id>/quick-add` |

#### 10.3 Response behavior

| Situation | Behavior |
|-----------|----------|
| successful GET | full HTML page |
| successful POST (non-HTMX) | redirect |
| successful POST (HTMX) | fragment HTML |
| validation failure | form error display inline |
| authorization failure | redirect to login or 403 |
| server error | generic error message plus structured logging |

---

### 11. Validation Architecture

Validation is enforced both for UX and for safety, but the server remains authoritative.

#### 11.1 Client-side validation

Used only for convenience:

- required fields
- numeric quantity bounds
- lightweight UI feedback

#### 11.2 Server-side validation

Mandatory for all writes:

- item name required
- quantity must be positive numeric
- note length limited
- unit length limited
- household membership required
- item must belong to current user’s household scope
- max household size enforced
- favorite reorder payload validated

#### 11.3 Input normalization

Item-relevant text is normalized for matching:

- trim whitespace
- collapse repeated spaces
- lowercase normalized version for comparisons
- optional accent normalization if needed later

The original display value should still be preserved for the UI.

---

### 12. Authentication and Authorization

#### 12.1 Authentication model

Use session-based authentication with local accounts.

**Components**

| Component | Choice |
|-----------|--------|
| Login | username/password login |
| Password hashing | password hash via Argon2 preferred, bcrypt acceptable |
| Sessions | Flask-Login session management |
| Cookies | secure cookie settings |

**Rationale**

Best balance of simplicity, privacy, and maintainability for a private app.

#### 12.2 Authorization model

Authorization is household-scoped.

**Rules**

- users can only access data belonging to their household
- owner can generate or rotate invite code if needed
- members can use grocery and favorites functions
- administrative controls stay minimal in v1

#### 12.3 Session security

- HttpOnly cookies
- Secure cookies in HTTPS environments
- SameSite=Lax or stricter
- session rotation on login
- CSRF protection on all state-changing forms

---

### 13. Concurrency and Consistency Model

#### 13.1 Problem

Two or more household members may edit the shared list at nearly the same time.

#### 13.2 Chosen solution

Rely on PostgreSQL transactions and deterministic application logic.

**Approach**

- each write occurs in a transaction
- database commit defines authoritative order
- duplicate adds are resolved via DB-enforced active dedupe index + atomic UPSERT
- after a write, the UI reloads current state
- page focus refresh and optional lightweight polling improve visibility of shared changes

#### 13.3 Conflict strategy

Use a practical last-committed-state model.

**Examples**

- if two users toggle the same item in close succession, the latest committed state is shown
- if two users add the same item concurrently, transactional duplicate-check logic should attempt merge behavior

#### 13.4 Why no queue lock

An in-memory Python queue or lock is not appropriate because:

- it does not protect across multiple processes
- it breaks under scaling or restart conditions
- it moves consistency concerns out of the database unnecessarily

#### 13.5 Optional future enhancement

If needed later, optimistic concurrency metadata such as updated_at or version counters can be exposed in the UI. This is not required for v1.

---

### 14. UI Architecture

#### 14.1 Rendering model

Server-rendered templates with HTMX fragments.

#### 14.2 Main views

- login/register
- household setup/join
- grocery list page
- favorites management page

#### 14.3 Mobile-first layout principles

- single primary page for daily use
- large touch targets
- minimal nested navigation
- sticky primary actions only when justified
- clear checked vs active visual distinction
- fast return to grocery list after every action

#### 14.4 Component groups

- top input/search section
- favorite quick-add row/grid
- active grocery item list
- checked item list
- confirm purchase action
- feedback message area

---

### 15. Deployment Architecture

#### 15.1 Deployment topology

For v1, use a two-container stack behind a **host-based reverse proxy**:

- application container (Flask + Gunicorn), bound to `127.0.0.1:18080` on the host
- PostgreSQL container, internal to the Docker network only
- **Nginx on the host** (not containerized) terminates HTTPS for `grocery.<your-domain>` and proxies to the web container
- **Certbot on the host** manages a Let's Encrypt certificate and auto-renews it every 60 days via a systemd timer

The web container is never exposed on the public interface; only Nginx listens on ports 80/443.

#### 15.2 Runtime stack

- Gunicorn serving Flask app (2 workers, 120 s timeout)
- PostgreSQL as persistent database
- Docker named volumes for database persistence
- `werkzeug.middleware.proxy_fix.ProxyFix` wraps the WSGI app in production so Flask trusts the `X-Forwarded-*` headers set by Nginx (required for `SESSION_COOKIE_SECURE` to work correctly behind TLS termination)

#### 15.3 Environment configuration

Use environment variables for:

- Flask secret key
- database URL
- password hashing config
- session cookie security flags
- `PREFERRED_URL_SCHEME=https` (so `url_for(_external=True)` produces HTTPS links)
- log level
- optional invite code settings

#### 15.4 Recommended environments

- local development (Docker Compose + Flask dev server)
- staging-like local compose environment (`compose.prod.yaml` against a throwaway `.env`)
- production on VPS with registered domain and Let's Encrypt TLS

#### 15.5 Subdomain pattern (future services)

The apex domain (`<your-domain>`) stays free for a landing page. Each service gets its own subdomain (e.g. `grocery.<your-domain>`, `openclaw.<your-domain>`), its own Nginx server block, and its own Let's Encrypt cert. Adding a service does not modify the grocery stack.

---

### 16. Security Architecture

#### 16.1 Security posture

This is a private app, but it still handles credentials and shared household data. Basic web security standards are required.

#### 16.2 Required controls

| Control |
|---------|
| hashed passwords |
| CSRF protection |
| secure session cookies |
| server-side validation |
| authorization checks on all household-scoped data |
| escaped HTML output by default |
| rate limiting on authentication endpoints |
| secrets outside source control |

#### 16.3 External exposure

If the app is reachable from the internet:

- HTTPS mandatory
- reverse proxy strongly recommended
- firewall restrictions where practical
- regular backups required

---

### 17. Observability and Logging

#### 17.1 Logging goals

- diagnose application errors
- trace core state-changing actions
- support debugging in a small deployment

#### 17.2 Logging approach

Use structured application logs for:

- authentication events
- household creation/join
- grocery add/toggle/confirm
- favorites add/remove/reorder
- validation failures
- unhandled exceptions

#### 17.3 Log destinations

- stdout in container
- optional file-based persistence if deployment requires it

#### 17.4 Monitoring

Formal monitoring stack is not required for v1. Minimum acceptable operational visibility:

- startup logs
- request error logs
- database connection error logs
- migration logs

---

### 18. Backup and Recovery

#### 18.1 Backup requirement

Because grocery state and credentials are persisted in PostgreSQL, database backups are mandatory for any persistent deployment.

#### 18.2 Minimum backup strategy

- daily PostgreSQL dump
- retain at least 7 recent backups
- store backups outside the running container
- verify restore procedure at least once

#### 18.3 Recovery objective

Given the app’s small scope, a simple documented restore procedure is sufficient.

---

### 19. Testing Strategy

#### 19.1 Testing goals

- verify core domain logic
- protect against regression in shared-list behavior
- ensure safe deployment changes

#### 19.2 Test layers

| Layer | Focus |
|-------|--------|
| **Unit tests** | normalization logic; duplicate merge behavior; permission helpers; item state transitions; favorite ordering logic |
| **Integration tests** | register/login flows; household creation/join; add item flow; toggle item flow; confirm purchase flow; household data isolation; concurrent-like action sequences |
| **Migration tests** | migrate up from empty database; migrate down where applicable; validate reproducibility in fresh environment |

#### 19.3 Tools

- pytest
- Flask test client
- temporary PostgreSQL test database or containerized test environment

---

### 20. Performance Expectations

#### 20.1 Expected scale

| Dimension | Expectation |
|-----------|-------------|
| Households | 1 per deployment, or a very small number |
| Active users | 2–5 |
| Request volume | low |
| Data volume | low |

#### 20.2 Performance target

The app should feel effectively instantaneous under normal home usage.

#### 20.3 Bottleneck expectations

None of significance in v1. Simplicity and correctness take priority over optimization.

---

### 21. Extensibility Strategy

The architecture should support future modules without redesigning the core.

#### 21.1 Likely future modules

- meal planner
- notes
- purchase history
- household analytics

#### 21.2 Extension method

Add new domain modules as additional blueprints and models while reusing:

- household scoping
- auth/session system
- common validation helpers
- deployment/runtime foundation

#### 21.3 Deliberate restraint

Do not pre-build generic plugin systems, event buses, or cross-module abstractions before they are needed.

---

### 22. Rejected Alternatives

| Alternative | Reason for rejection |
|-------------|----------------------|
| SQLite | PostgreSQL gives cleaner transactional behavior and more reliable concurrent write handling |
| SPA frontend | Unnecessary client-state complexity, extra build tooling, and stronger API dependency for little practical gain |
| WebSockets | Lightweight polling and refresh-based synchronization are sufficient for the expected user count in v1 |
| Microservices | Domain and load do not justify distributed system complexity |
| In-process write queue | Brittle, process-local, and inferior to proper database transaction handling |

---

### 23. Implementation Constraints

- System must remain maintainable by a single developer
- Operational footprint must stay small
- Architecture must support safe future expansion without premature abstraction
- All design decisions should be understandable without extensive framework-specific indirection

---

### 24. Architecture Decision Summary

| Decision | Choice |
|----------|--------|
| Pattern | Modular monolith |
| Backend | Flask |
| Frontend | Server-rendered Jinja templates + Tailwind + HTMX |
| Database | PostgreSQL |
| Auth | Local session-based authentication |
| Deployment | Docker Compose |
| Consistency model | Transactional writes with database as source of truth |
| Real-time model | post-action refresh + optional polling |
| Scope discipline | grocery list and favorites only in v1 |

---

### 25. Acceptance Criteria for the Architecture Baseline

The architecture is considered approved when:

- module boundaries are accepted
- persistence model is accepted
- concurrency approach is accepted
- deployment model is accepted
- auth/session design is accepted
- v1 interaction model is accepted
- no unresolved decision blocks initial implementation

---

### 26. Immediate Next Documents After This

After this specification, the next most useful engineering documents are:

- Database Schema Specification
- Route and Form Contract Specification
- Implementation Roadmap

If you want, I will draft the Database Schema Specification next in the same professional format.
