# Database Schema Specification - V1 MVP

This schema strictly targets PostgreSQL 16+. It enforces data integrity at the database level to prevent bad state from entering the system during concurrent household edits.
### 1.1 `household`

| Column      | Type           | Constraints                             | Description                    |
| :---------- | :------------- | :-------------------------------------- | :----------------------------- |
| `id`        | `SERIAL`       | `PRIMARY KEY`                           | Unique identifier.             |
| `name`      | `VARCHAR(100)` | `NOT NULL`                              | Display name of the household. |
| `invite_code` | `VARCHAR(32)`  | `NOT NULL, UNIQUE`                      | Cryptographically secure random string. |
| `created_at`  | `TIMESTAMPTZ`  | `NOT NULL, DEFAULT NOW()`               | Timestamp of creation.         |

### 1.2 `users`

| Column        | Type           | Constraints                                                    | Description                        |
| :------------ | :------------- | :------------------------------------------------------------- | :--------------------------------- |
| `id`          | `SERIAL`       | `PRIMARY KEY`                                                  | Unique identifier.                 |
| `household_id` | `INTEGER`      | `NOT NULL, REFERENCES household(id) ON DELETE CASCADE`         | Household association.             |
| `username`    | `VARCHAR(50)`  | `NOT NULL, UNIQUE`                                             | Login identifier.                  |
| `password_hash` | `VARCHAR(255)` | `NOT NULL`                                                     | Argon2 or bcrypt hash.             |
| `role`        | `VARCHAR(20)`  | `NOT NULL`                                                     | Enforced via application logic ('owner', 'member'). |
| `is_active`   | `BOOLEAN`      | `NOT NULL, DEFAULT TRUE`                                       | Soft-delete/deactivation toggle.   |
| `created_at`  | `TIMESTAMPTZ`  | `NOT NULL, DEFAULT NOW()`                                      | Timestamp of creation.             |

### 1.3 `grocery_item`

| Column              | Type            | Constraints                                                        | Description                                       |
| :------------------ | :-------------- | :----------------------------------------------------------------- | :------------------------------------------------ |
| `id`                | `SERIAL`        | `PRIMARY KEY`                                                      | Unique identifier.                                |
| `household_id`      | `INTEGER`       | `NOT NULL, REFERENCES household(id) ON DELETE CASCADE`             | Household association.                            |
| `name`              | `VARCHAR(100)`  | `NOT NULL`                                                         | Original user input.                              |
| `normalized_name`   | `VARCHAR(100)`  | `NOT NULL`                                                         | Lowercased, stripped string for duplicate detection. |
| `quantity_value`    | `NUMERIC(10,2)` | `NOT NULL, DEFAULT 1.00`                                           | Supports decimals (e.g., 1.5 kg).                 |
| `unit`              | `VARCHAR(20)`   | `NULL`                                                             | Optional unit (kg, stück, flasche).                  |
| `note`              | `VARCHAR(255)`  | `NULL`                                                             | Optional descriptor.                              |
| `status`            | `VARCHAR(20)`   | `NOT NULL, DEFAULT 'active'`                                      | State restriction ('active', 'checked').          |
| `checked_by_user_id` | `INTEGER`       | `REFERENCES users(id) ON DELETE SET NULL`                          | Audit trail for shopping.                         |
| `checked_at`        | `TIMESTAMPTZ`   | `NULL`                                                             | Timestamp of state change.                        |
| `created_by_user_id` | `INTEGER`       | `NOT NULL, REFERENCES users(id) ON DELETE RESTRICT`                | Original author.                                  |
| `created_at`        | `TIMESTAMPTZ`   | `NOT NULL, DEFAULT NOW()`                                         | Timestamp of creation.                            |
| `updated_at`        | `TIMESTAMPTZ`   | `NOT NULL, DEFAULT NOW()`                                         | Timestamp of last modification.                   |

### 1.4 `favorite_item`

| Column                 | Type            | Constraints                                                | Description                |
| :--------------------- | :-------------- | :--------------------------------------------------------- | :------------------------- |
| `id`                   | `SERIAL`        | `PRIMARY KEY`                                              | Unique identifier.         |
| `household_id`         | `INTEGER`       | `NOT NULL, REFERENCES household(id) ON DELETE CASCADE`     | Household association.     |
| `name`                 | `VARCHAR(100)`  | `NOT NULL`                                                 | Original user input.       |
| `normalized_name`      | `VARCHAR(100)`  | `NOT NULL`                                                 | Used for dropdown suggestions. |
| `default_quantity_value` | `NUMERIC(10,2)` | `NOT NULL, DEFAULT 1.00`                                   | Quick-add default.         |
| `default_unit`         | `VARCHAR(20)`   | `NULL`                                                     | Quick-add default.         |
| `default_note`         | `VARCHAR(255)`  | `NULL`                                                     | Quick-add default.         |
| `sort_order`           | `INTEGER`       | `NOT NULL, DEFAULT 0`                                      | UI ordering integer.       |
| `created_at`           | `TIMESTAMPTZ`   | `NOT NULL, DEFAULT NOW()`                                  | Timestamp of creation.     |
| `updated_at`           | `TIMESTAMPTZ`   | `NOT NULL, DEFAULT NOW()`                                  | Timestamp of last modification. |

2. API & Route Specifications

The application relies on standard form submissions and HTMX partial requests. There are no JSON-based REST endpoints in this architecture. All data payloads are application/x-www-form-urlencoded.

2.1 Authentication & Household Routes (Standard HTML)
Method,Endpoint,Payload / Form Data,Response
GET,/login,None,Full HTML Page (Login form)
POST,/login,"username, password",302 Redirect to /grocery or 401 Form Error
POST,/logout,None,302 Redirect to /login
POST,/household/join,invite_code,302 Redirect to /grocery

2.2 Grocery Routes (HTMX Optimized)
Method,Endpoint,Payload / Form Data,Response
GET,/grocery,None,Full HTML Page
GET,/grocery/search,q (Query string),HTML Fragment (Dropdown list of <li> items matching favorites/history)
POST,/grocery/items,"name, quantity, unit, note",HTML Fragment (Updated active items list) OR 302 Redirect
POST,/grocery/items/<id>/toggle,None,HTML Fragment (The updated individual item <tr> or <li> to be swapped)
POST,/grocery/confirm,None,HTML Fragment (Clears the checked items list) OR 302 Redirect

2.3 Favorites Routes (HTMX Optimized)
Method,Endpoint,Payload / Form Data,Response
GET,/favorites,None,Full HTML Page
POST,/favorites,"name, quantity, unit, note",HTML Fragment (Updated favorites list)
DELETE,/favorites/<id>,None,200 OK (Empty response to remove DOM element)
POST,/favorites/<id>/quick-add,None,HTML Fragment (Feedback message + triggers list refresh)

3. UI & HTMX Component Specifications

The UI avoids complex state management by leveraging HTMX attributes directly on HTML elements to dictate backend interactions and DOM swaps.
3.1 Global Layout (base.html)

    Viewport: <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no"> to prevent input zoom on mobile browsers.

    Navigation: Bottom fixed navigation bar (Tailwind: fixed bottom-0 w-full border-t bg-white).

3.2 Add Item Component & Search

    Search Input: A text input with an HTMX trigger for real-time suggestions.

    HTMX Attributes on Input:

        hx-get="/grocery/search"

        hx-trigger="keyup changed delay:300ms, search"

        hx-target="#search-results"

        hx-swap="innerHTML"

    Form Submission: Submitting the form posts to /grocery/items, targeting the main list container to swap the newly appended item.

3.3 Active Grocery List Component

    List Item Structure: Flexbox container for row layout (Tailwind: flex justify-between items-center p-4 border-b).

    Toggle Action: Clicking the checkbox or item row fires a toggle request.

    HTMX Attributes on Row:

        hx-post="/grocery/items/{{ item.id }}/toggle"

        hx-target="this"

        hx-swap="outerHTML"

    State Styling: Checked items receive distinct styling (Tailwind: line-through text-gray-400 bg-gray-50) applied server-side before the HTML fragment is returned.

3.4 Confirm Purchase Component

    Trigger: A sticky button located below the checked items list.

    Behavior: Fires hx-post="/grocery/confirm".

    HTMX Attributes:

        hx-target="#checked-items-container"

        hx-swap="innerHTML" (replaces the container with an empty state or success message).

3.5 Polling Implementation (Optional/V1 Edge Case)

    To keep multiple users in sync without WebSockets, the main list container can utilize HTMX polling.

    HTMX Attributes: hx-get="/grocery/fragments/list" hx-trigger="every 15s" hx-swap="innerHTML".


### V2 Roadmap Note: Historical Data & Indexing

- **Analytics Implementation:** For future data analysis (e.g., purchase history, frequency statistics), do **not** introduce an `archived` status to the `grocery_item` table. Doing so will bloat the active state table and severely degrade the core application's performance.
- **Required Architecture:** Implement a separate, append-only `purchase_history` ledger. The "Confirm Purchase" action must be updated as a two-step transaction: copy the `checked` items to this ledger, then execute the hard-delete from `grocery_item`.
- **Indexing Restoration:** Once historical tables are introduced and row counts scale beyond a single database page (typically >100 rows), composite indexes (e.g., `household_id` + `status`, or `household_id` + `normalized_name`) must be explicitly applied to maintain query speeds.
