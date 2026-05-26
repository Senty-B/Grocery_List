# Vendored third-party assets

These libraries are vendored (not loaded from a CDN at runtime) to remove
the supply-chain risk of trusting an external host on every page load.

| File                       | Version  | Source                                                          |
| -------------------------- | -------- | --------------------------------------------------------------- |
| `htmx-1.9.10.min.js`       | 1.9.10   | https://unpkg.com/htmx.org@1.9.10/dist/htmx.min.js              |
| `tailwindcss-3.4.16.js`    | 3.4.16   | https://cdn.tailwindcss.com/3.4.16                              |

## Updating

1. Download the new pinned version from the source URL above with the
   version number changed.
2. Rename the file in place (e.g. `htmx-1.9.11.min.js`).
3. Update the corresponding `url_for('static', ...)` call in
   `app/templates/base.html`.
4. Commit the new file together with the template change.

Never reference a `@latest` URL or an unversioned CDN path from the
templates — that re-introduces the supply-chain risk this folder
exists to eliminate.
