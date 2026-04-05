# Database Schema Specification - V1 MVP

This schema strictly targets PostgreSQL 16+. It enforces data integrity at the database level to prevent bad state from entering the system during concurrent household edits.

### 1.1 `household`


| Column        | Type           | Constraints               | Description                             |
| ------------- | -------------- | ------------------------- | --------------------------------------- |
| `id`          | `SERIAL`       | `PRIMARY KEY`             | Unique identifier.                      |
| `name`        | `VARCHAR(100)` | `NOT NULL`                | Display name of the household.          |
| `invite_code` | `VARCHAR(32)`  | `NOT NULL, UNIQUE`        | Cryptographically secure random string. |
| `created_at`  | `TIMESTAMPTZ`  | `NOT NULL, DEFAULT NOW()` | Timestamp of creation.                  |


### 1.2 `users`


| Column          | Type           | Constraints                                            | Description                                         |
| --------------- | -------------- | ------------------------------------------------------ | --------------------------------------------------- |
| `id`            | `SERIAL`       | `PRIMARY KEY`                                          | Unique identifier.                                  |
| `household_id`  | `INTEGER`      | `NOT NULL, REFERENCES household(id) ON DELETE CASCADE` | Household association.                              |
| `username`      | `VARCHAR(50)`  | `NOT NULL, UNIQUE`                                     | Login identifier.                                   |
| `password_hash` | `VARCHAR(255)` | `NOT NULL`                                             | bcrypt hash.                                        |
| `role`          | `VARCHAR(20)`  | `NOT NULL`                                             | Enforced via application logic ('owner', 'member'). |
| `is_active`     | `BOOLEAN`      | `NOT NULL, DEFAULT TRUE`                               | Soft-delete/deactivation toggle.                    |
| `created_at`    | `TIMESTAMPTZ`  | `NOT NULL, DEFAULT NOW()`                              | Timestamp of creation.                              |


### 1.3 `grocery_item`


| Column               | Type            | Constraints                                            | Description                                          |
| -------------------- | --------------- | ------------------------------------------------------ | ---------------------------------------------------- |
| `id`                 | `SERIAL`        | `PRIMARY KEY`                                          | Unique identifier.                                   |
| `household_id`       | `INTEGER`       | `NOT NULL, REFERENCES household(id) ON DELETE CASCADE` | Household association.                               |
| `name`               | `VARCHAR(100)`  | `NOT NULL`                                             | Original user input.                                 |
| `normalized_name`    | `VARCHAR(100)`  | `NOT NULL`                                             | Lowercased, stripped string for duplicate detection. |
| `quantity_value`     | `NUMERIC(10,2)` | `NOT NULL, DEFAULT 1.00`                               | Supports decimals (e.g., 1.5 kg).                    |
| `unit`               | `VARCHAR(20)`   | `NULL`                                                 | Optional unit (kg, stück, flasche).                  |
| `note`               | `VARCHAR(255)`  | `NULL`                                                 | Optional descriptor.                                 |
| `status`             | `VARCHAR(20)`   | `NOT NULL, DEFAULT 'active'`                           | State restriction ('active', 'checked').             |
| `checked_by_user_id` | `INTEGER`       | `REFERENCES users(id) ON DELETE SET NULL`              | Audit trail for shopping.                            |
| `checked_at`         | `TIMESTAMPTZ`   | `NULL`                                                 | Timestamp of state change.                           |
| `created_by_user_id` | `INTEGER`       | `NOT NULL, REFERENCES users(id) ON DELETE RESTRICT`    | Original author.                                     |
| `created_at`         | `TIMESTAMPTZ`   | `NOT NULL, DEFAULT NOW()`                              | Timestamp of creation.                               |
| `updated_at`         | `TIMESTAMPTZ`   | `NOT NULL, DEFAULT NOW()`                              | Timestamp of last modification.                      |


### 1.4 `favorite_item`


| Column                   | Type            | Constraints                                            | Description                     |
| ------------------------ | --------------- | ------------------------------------------------------ | ------------------------------- |
| `id`                     | `SERIAL`        | `PRIMARY KEY`                                          | Unique identifier.              |
| `household_id`           | `INTEGER`       | `NOT NULL, REFERENCES household(id) ON DELETE CASCADE` | Household association.          |
| `name`                   | `VARCHAR(100)`  | `NOT NULL`                                             | Original user input.            |
| `normalized_name`        | `VARCHAR(100)`  | `NOT NULL`                                             | Used for dropdown suggestions.  |
| `default_quantity_value` | `NUMERIC(10,2)` | `NOT NULL, DEFAULT 1.00`                               | Quick-add default.              |
| `default_unit`           | `VARCHAR(20)`   | `NULL`                                                 | Quick-add default.              |
| `default_note`           | `VARCHAR(255)`  | `NULL`                                                 | Quick-add default.              |
| `sort_order`             | `INTEGER`       | `NOT NULL, DEFAULT 0`                                  | UI ordering integer.            |
| `created_at`             | `TIMESTAMPTZ`   | `NOT NULL, DEFAULT NOW()`                              | Timestamp of creation.          |
| `updated_at`             | `TIMESTAMPTZ`   | `NOT NULL, DEFAULT NOW()`                              | Timestamp of last modification. |


The application relies on standard form submissions and HTMX partial requests. There are no JSON-based REST endpoints; all payloads use `application/x-www-form-urlencoded`.

## 2. API & Route Specification

### 2.1 Authentication & household routes (standard HTML)


| Method | Endpoint          | Payload / form data    | Response                                                |
| ------ | ----------------- | ---------------------- | ------------------------------------------------------- |
| `GET`  | `/login`          | None                   | Full HTML page (login form).                            |
| `POST` | `/login`          | `username`, `password` | `302` redirect to `/grocery`, or `401` with form error. |
| `POST` | `/logout`         | None                   | `302` redirect to `/login`.                             |
| `POST` | `/household/join` | `invite_code`          | `302` redirect to `/grocery`.                           |


### 2.2 Grocery routes (HTMX)


| Method | Endpoint                     | Payload / form data                | Response                                                            |
| ------ | ---------------------------- | ---------------------------------- | ------------------------------------------------------------------- |
| `GET`  | `/grocery`                   | None                               | Full HTML page.                                                     |
| `GET`  | `/grocery/search`            | `q` (query string)                 | HTML fragment: dropdown of `<li>` items matching favorites/history. |
| `POST` | `/grocery/items`             | `name`, `quantity`, `unit`, `note` | HTML fragment (updated active list) or `302` redirect.              |
| `POST` | `/grocery/items/<id>/toggle` | None                               | HTML fragment: updated row (`<tr>` or `<li>`) for swap.             |
| `POST` | `/grocery/confirm`           | None                               | HTML fragment (clears checked list) or `302` redirect.              |


### 2.3 Favorites routes (HTMX)


| Method   | Endpoint                    | Payload / form data                | Response                                         |
| -------- | --------------------------- | ---------------------------------- | ------------------------------------------------ |
| `GET`    | `/favorites`                | None                               | Full HTML page.                                  |
| `POST`   | `/favorites`                | `name`, `quantity`, `unit`, `note` | HTML fragment (updated favorites list).          |
| `DELETE` | `/favorites/<id>`           | None                               | `200 OK`, empty body (remove DOM node).          |
| `POST`   | `/favorites/<id>/quick-add` | None                               | HTML fragment (feedback + list refresh trigger). |


The UI avoids complex client-side state by attaching HTMX attributes to HTML elements for backend calls and DOM swaps.

### 3.1 Global layout (`base.html`)


| Concern        | Specification                                                                                                                                           |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Viewport**   | `<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">` — reduces unwanted zoom on mobile inputs. |
| **Navigation** | Bottom-fixed bar (Tailwind: `fixed bottom-0 w-full border-t bg-white`).                                                                                 |


### 3.2 Add item & search


| Concern          | Specification                                                                      |
| ---------------- | ---------------------------------------------------------------------------------- |
| **Search input** | Text input with HTMX-driven live suggestions.                                      |
| **Form submit**  | `POST` to `/grocery/items`; target the main list container to swap in the new row. |


**HTMX on search input**


| Attribute    | Value                               |
| ------------ | ----------------------------------- |
| `hx-get`     | `/grocery/search`                   |
| `hx-trigger` | `keyup changed delay:300ms, search` |
| `hx-target`  | `#search-results`                   |
| `hx-swap`    | `innerHTML`                         |


### 3.3 Active grocery list


| Concern           | Specification                                                                                                                |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| **Row layout**    | Flex row (Tailwind: `flex justify-between items-center p-4 border-b`).                                                       |
| **Toggle**        | Checkbox or row click issues the toggle request.                                                                             |
| **Checked state** | Server renders strikethrough/muted styles (Tailwind: `line-through text-gray-400 bg-gray-50`) before returning the fragment. |


**HTMX on row**


| Attribute   | Value                                 |
| ----------- | ------------------------------------- |
| `hx-post`   | `/grocery/items/{{ item.id }}/toggle` |
| `hx-target` | `this`                                |
| `hx-swap`   | `outerHTML`                           |


### 3.4 Confirm purchase


| Concern     | Specification                                |
| ----------- | -------------------------------------------- |
| **Trigger** | Sticky control below the checked-items list. |
| **Action**  | `hx-post="/grocery/confirm"`.                |


**HTMX on confirm control**


| Attribute   | Value                                                      |
| ----------- | ---------------------------------------------------------- |
| `hx-target` | `#checked-items-container`                                 |
| `hx-swap`   | `innerHTML` — replace with empty state or success message. |


### 3.5 Polling (optional / V1 edge case)

Without WebSockets, the main list can stay loosely in sync via HTMX polling on the list container.


| Attribute    | Value                     |
| ------------ | ------------------------- |
| `hx-get`     | `/grocery/fragments/list` |
| `hx-trigger` | `every 15s`               |
| `hx-swap`    | `innerHTML`               |


### V2 Roadmap Note: Historical Data & Indexing

- **Analytics Implementation:** For future data analysis (e.g., purchase history, frequency statistics), do **not** introduce an `archived` status to the `grocery_item` table. Doing so will bloat the active state table and severely degrade the core application's performance.
- **Required Architecture:** Implement a separate, append-only `purchase_history` ledger. The "Confirm Purchase" action must be updated as a two-step transaction: copy the `checked` items to this ledger, then execute the hard-delete from `grocery_item`.
- **Indexing Restoration:** Once historical tables are introduced and row counts scale beyond a single database page (typically >100 rows), composite indexes (e.g., `household_id` + `status`, or `household_id` + `normalized_name`) must be explicitly applied to maintain query speeds.

