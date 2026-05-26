# Route Contract - V1 (Canonical Source of Truth)

> **Status:** Canonical for v1 implementation  
> **Scope:** Server-rendered Flask app with HTMX partial updates  
> **Purpose:** Eliminate route ambiguity across roadmap, architecture, and implementation docs

---

## 1) Contract Principles

- This app is **HTML-first**, not a public REST API.
- `GET` routes return full pages or HTML fragments.
- State-changing actions use `POST` for predictable form + CSRF behavior.
- Payload format is `application/x-www-form-urlencoded`.
- For v1 consistency, deletion actions are modeled as explicit commands:
  - `POST /favorites/<id>/delete` (preferred over `DELETE /favorites/<id>`).

---

## 2) Route Naming Rules

- Use plural nouns for collections: `/favorites`, `/grocery/items`.
- Use path params for target resources: `/<id>`.
- Use explicit action suffixes for non-CRUD commands:
  - `/toggle`
  - `/confirm`
  - `/quick-add`
  - `/delete`
  - `/reorder`
- Do not introduce alternate aliases for the same action in v1.

---

## 3) Authentication and Session Routes

| Method | Path | Purpose | Request | Response |
|---|---|---|---|---|
| `GET` | `/login` | Render login page | none | `200` HTML page |
| `POST` | `/login` | Authenticate user | `username`, `password` | `302` redirect on success, inline form error on failure |
| `POST` | `/logout` | End session | CSRF-protected form post | `302` redirect to `/login` |
| `GET` | `/register` | Render registration page | none | `200` HTML page |
| `POST` | `/register` | Create owner + household | registration form fields | `302` redirect on success, inline form error on failure |

---

## 4) Household Routes

| Method | Path | Purpose | Request | Response |
|---|---|---|---|---|
| `GET` | `/household` | Household overview page | none | `200` HTML page |
| `POST` | `/household/join` | Join household with invite code | `invite_code` | `302` redirect to `/grocery` or inline form error |
| `POST` | `/household/rotate-code` | Rotate invite code (owner only) | none | `200` HTML fragment or `302` redirect |

---

## 5) Grocery Routes

| Method | Path | Purpose | Request | Response |
|---|---|---|---|---|
| `GET` | `/grocery` | Main grocery page | none | `200` HTML page |
| `GET` | `/grocery/search` | Search suggestions for add flow | query `q` | `200` HTML fragment |
| `POST` | `/grocery/items` | Add item / merge duplicate quantity | `name`, `quantity`, `unit`, `note` | fragment for HTMX, `302` fallback for full form |
| `POST` | `/grocery/items/<id>/toggle` | Toggle active/checked | none | `200` HTML fragment (row/list refresh) |
| `POST` | `/grocery/confirm` | Permanently remove checked items | none | `200` HTML fragment (checked list cleared) |
| `GET` | `/grocery/fragments/list` | Optional polling fragment | none | `200` HTML fragment |

---

## 6) Favorites Routes

| Method | Path | Purpose | Request | Response |
|---|---|---|---|---|
| `GET` | `/favorites` | Favorites management page | none | `200` HTML page |
| `POST` | `/favorites` | Create favorite | `name`, `quantity`, `unit`, `note` | `200` HTML fragment |
| `POST` | `/favorites/<id>/delete` | Remove favorite | none | `200` HTML fragment or empty success response |
| `POST` | `/favorites/<id>/reorder` | Change favorite sort order | reorder payload | `200` HTML fragment |
| `POST` | `/favorites/<id>/quick-add` | Add favorite to grocery list | optional quantity override | `200` HTML fragment |

---

## 7) HTMX Contract Rules

- HTMX requests are detected via `HX-Request: true`.
- For HTMX:
  - return partial template fragments (not full layout),
  - use `200` with renderable HTML,
  - use consistent targets/swaps per template contract.
- For non-HTMX form posts:
  - use `302` redirect to the canonical page route.

Recommended mapping:

- Add item -> target list container, swap `innerHTML`/`beforeend` as appropriate.
- Toggle item -> target row, swap `outerHTML`.
- Delete favorite -> target favorite row/container, swap `delete` or replaced fragment.
- Confirm purchase -> target checked-items container, swap `innerHTML`.

---

## 8) Security and Validation Requirements (Route-Level)

- All state-changing routes must be CSRF-protected.
- All non-public routes require authenticated user.
- Household-scoped authorization is mandatory for all household resources.
- Server-side validation is authoritative; client-side checks are UX only.
- Use shared validation helpers for:
  - item name,
  - quantity,
  - note and unit length/format,
  - invite code shape.

---

## 9) Error Handling Contract

- Validation errors:
  - HTMX: return fragment with inline field/message errors.
  - Non-HTMX: re-render form with validation messages.
- Authorization failures:
  - unauthenticated -> redirect to `/login`,
  - unauthorized -> `403` page/fragment.
- Not found:
  - return `404` page or fragment-safe response.
- Server errors:
  - return generic user-safe error message,
  - log structured error with route and correlation context.

---

## 10) Explicit Decision: Why `POST /favorites/<id>/delete`

The v1 app uses server-rendered forms and HTMX, not a public external REST API.  
Using `POST /favorites/<id>/delete` gives:

- native HTML form compatibility,
- straightforward CSRF handling in Flask forms,
- less implementation variance between HTMX and non-HTMX flows,
- one consistent pattern for AI agents and developers.

If a public API is introduced in v2+, method semantics can be revised behind an API version boundary.

---

## 11) Change Control

- Any route change must be made in this file first.
- `Technical Architecture.md`, `Schema_API_UI_sub_specs.md`, and `Implementation_Roadmap.md` must reference this contract and remain aligned.
- During code review, route mismatches are blocking issues.

