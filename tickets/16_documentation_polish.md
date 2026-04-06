# Ticket 16: Documentation & Final Polish

**Phase:** 5 — Hardening & Polish  
**Priority:** Medium  
**Dependencies:** All prior tickets  
**Estimated effort:** Small

---

## Why This Matters

Documentation lets someone else (or future you) set up and maintain the project. Final polish ensures the app feels solid in daily use.

---

## Tasks

### 1. Write `README.md`

Include:
- Project overview (1 paragraph)
- Tech stack summary
- Prerequisites (Python 3.12+, Docker, PostgreSQL)
- Local development setup (step by step)
- Running tests
- Docker Compose usage
- Production deployment (link to `Production_Cutover_Runbook.md`)
- Environment variables table

### 2. Add loading states

For HTMX interactions, add visual feedback:
- `hx-indicator` class on buttons to show a spinner while requests are in flight
- Add CSS for `.htmx-request` state

Example:
```html
<button type="submit" class="... htmx-indicator-parent">
  <span class="htmx-indicator hidden">
    <svg class="animate-spin h-5 w-5" ...></svg>
  </span>
  Add Item
</button>
```

### 3. Add empty states

Every list page should have a friendly message when empty:
- Empty grocery list: "No items yet. Add something above!"
- Empty favorites: "No favorites yet. Add your first one!"
- Empty checked items: (section hidden entirely)

### 4. Accessibility review

- All `<input>` fields have `<label>` elements
- All buttons have descriptive text (not just icons)
- Color contrast ratio meets WCAG AA (4.5:1 for text)
- Focus indicators are visible on all interactive elements
- `aria-label` on icon-only buttons

### 5. Final functional walkthrough

Test the complete happy path on a phone:
1. Register → creates household
2. Copy invite code → second user joins
3. Add items → they appear on the list
4. Toggle items → they move to checked
5. Confirm purchase → checked items removed
6. Add favorites → quick-add works
7. Logout / Login cycle works

---

## Acceptance Criteria

- [ ] `README.md` lets a new developer set up the project in under 30 minutes
- [ ] All pages have appropriate empty states
- [ ] Loading indicators appear during HTMX requests
- [ ] All form inputs have labels
- [ ] App is functional end-to-end on a mobile browser
- [ ] No JavaScript console errors in any flow
