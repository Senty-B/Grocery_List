# Ticket 11: Favorites Page & Auth Templates Styling

**Phase:** 3 — Frontend & UI  
**Priority:** High  
**Dependencies:** Ticket 10  
**Estimated effort:** Medium

---

## Why This Matters

The favorites management page and the auth pages (login, register, join) need full styling to be usable on mobile.

---

## Tasks

### 1. Build the favorites management page

`app/templates/favorites/index.html`:

```html
{% extends "base.html" %}
{% block title %}Favorites{% endblock %}

{% block content %}
<h1 class="text-xl font-bold text-gray-900 mb-4">Manage Favorites</h1>

<!-- Add favorite form -->
<form hx-post="{{ url_for('favorites.create') }}"
      hx-target="#favorites-list"
      hx-swap="innerHTML"
      class="mb-6 space-y-2 p-4 bg-white rounded-lg shadow-sm">
  {{ form.hidden_tag() }}
  {{ form.name(placeholder="Item name", class="w-full p-3 border border-gray-300 rounded-lg text-base") }}
  <div class="flex gap-2">
    {{ form.quantity(placeholder="Qty", class="w-20 p-3 border border-gray-300 rounded-lg text-base") }}
    {{ form.unit(placeholder="Unit", class="flex-1 p-3 border border-gray-300 rounded-lg text-base") }}
    {{ form.note(placeholder="Note", class="flex-1 p-3 border border-gray-300 rounded-lg text-base") }}
  </div>
  <button type="submit"
          class="w-full py-3 bg-yellow-500 text-white rounded-lg font-medium text-base
                 active:bg-yellow-700 transition-colors">
    Add to Favorites
  </button>
</form>

<!-- Favorites list -->
<div id="favorites-list">
  {% include 'favorites/_list.html' %}
</div>
{% endblock %}
```

### 2. Build the favorites list fragment

`app/templates/favorites/_list.html`:

```html
{% if favorites %}
<ul class="space-y-2">
  {% for fav in favorites %}
  <li class="flex items-center justify-between p-4 bg-white rounded-lg shadow-sm">
    <div class="flex-1 min-w-0">
      <p class="text-base font-medium text-gray-900 truncate">{{ fav.name }}</p>
      <p class="text-xs text-gray-400">
        {{ fav.default_quantity_value }}{% if fav.default_unit %} {{ fav.default_unit }}{% endif %}
        {% if fav.default_note %} · {{ fav.default_note }}{% endif %}
      </p>
    </div>
    <div class="flex gap-2 ml-2">
      <button hx-post="{{ url_for('favorites.quick_add', favorite_id=fav.id) }}"
              class="px-3 py-2 bg-blue-100 text-blue-700 rounded-lg text-sm font-medium
                     active:bg-blue-200 transition-colors">
        + List
      </button>
      <button hx-post="{{ url_for('favorites.delete', favorite_id=fav.id) }}"
              hx-target="closest li"
              hx-swap="outerHTML"
              hx-confirm="Remove this favorite?"
              class="px-3 py-2 bg-red-100 text-red-700 rounded-lg text-sm font-medium
                     active:bg-red-200 transition-colors">
        Delete
      </button>
    </div>
  </li>
  {% endfor %}
</ul>
{% else %}
<p class="text-gray-400 text-center py-8">No favorites yet. Add one above!</p>
{% endif %}
```

### 3. Style the auth pages

Update `login.html`, `register.html`, and `join.html` with full Tailwind styling:

- Centered card layout
- Large, clear form fields
- Submit buttons at least 44px tall
- Links between login/register/join pages
- Error messages displayed inline below fields

### 4. Build the household page

`app/templates/household/index.html`:

```html
{% extends "base.html" %}
{% block title %}Household{% endblock %}

{% block content %}
<h1 class="text-xl font-bold text-gray-900 mb-4">{{ household.name }}</h1>

{% if is_owner %}
<div class="p-4 bg-white rounded-lg shadow-sm mb-4">
  <h2 class="text-sm font-semibold text-gray-500 uppercase mb-2">Invite Code</h2>
  <p class="text-2xl font-mono font-bold text-blue-600 tracking-widest text-center py-2">
    {{ household.invite_code }}
  </p>
  <p class="text-xs text-gray-400 text-center mb-3">Share this code for others to join</p>
  <form method="POST" action="{{ url_for('household.rotate_code') }}">
    {{ csrf_token() | safe }}
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
    <button type="submit"
            class="w-full py-2 bg-gray-200 text-gray-700 rounded-lg text-sm
                   active:bg-gray-300 transition-colors">
      Generate New Code
    </button>
  </form>
</div>
{% endif %}

<div class="p-4 bg-white rounded-lg shadow-sm">
  <h2 class="text-sm font-semibold text-gray-500 uppercase mb-2">
    Members ({{ members|length }}/5)
  </h2>
  <ul class="divide-y divide-gray-100">
    {% for member in members %}
    <li class="flex items-center justify-between py-3">
      <span class="text-base text-gray-900">{{ member.username }}</span>
      <span class="text-xs px-2 py-1 rounded-full
        {% if member.role == 'owner' %}bg-yellow-100 text-yellow-700{% else %}bg-gray-100 text-gray-500{% endif %}">
        {{ member.role }}
      </span>
    </li>
    {% endfor %}
  </ul>
</div>

<form method="POST" action="{{ url_for('auth.logout') }}" class="mt-6">
  <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
  <button type="submit"
          class="w-full py-3 bg-red-100 text-red-700 rounded-lg font-medium text-base
                 active:bg-red-200 transition-colors">
    Log Out
  </button>
</form>
{% endblock %}
```

### 5. Quick-add feedback fragment

`app/templates/favorites/_quick_add_feedback.html`:

```html
{% if success %}
<span class="text-green-600 text-sm animate-pulse">Added!</span>
{% endif %}
```

---

## Acceptance Criteria

- [ ] Favorites page displays all household favorites in order
- [ ] "Add to Favorites" form works without page reload (HTMX)
- [ ] "Delete" removes the favorite row without page reload
- [ ] "+ List" quick-adds the item to the grocery list
- [ ] Login, register, and join pages are styled and usable on mobile
- [ ] Household page shows invite code to owner, member list to everyone
- [ ] Logout button works
- [ ] All pages have consistent styling via `base.html`
