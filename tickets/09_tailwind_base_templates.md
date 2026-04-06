# Ticket 9: Tailwind CSS Setup & Base Templates

**Phase:** 3 — Frontend & UI  
**Priority:** Critical  
**Dependencies:** Ticket 1  
**Estimated effort:** Small

---

## Why This Matters

The app is mobile-first. Tailwind CSS provides utility classes for fast, responsive styling without writing custom CSS files. HTMX enables partial page updates without a JavaScript framework.

## Reference

- UI specs: `Schema_API_UI_sub_specs.md` sections 3.1–3.5

---

## Tasks

### 1. Add Tailwind and HTMX via CDN to the base template

For v1, using CDN links is simpler than a build step. Update `app/templates/base.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>{% block title %}Grocery List{% endblock %}</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://unpkg.com/htmx.org@1.9.10"></script>
  <meta name="csrf-token" content="{{ csrf_token() }}">
  <style>
    /* Prevent iOS zoom on input focus */
    input, select, textarea { font-size: 16px; }
  </style>
</head>
<body class="bg-gray-50 min-h-screen pb-20">
  <!-- Flash messages -->
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
    <div id="flash-messages" class="fixed top-0 left-0 right-0 z-50 p-2">
      {% for category, message in messages %}
      <div class="max-w-lg mx-auto mb-2 p-3 rounded-lg text-sm
        {% if category == 'error' %}bg-red-100 text-red-700 border border-red-300
        {% elif category == 'success' %}bg-green-100 text-green-700 border border-green-300
        {% else %}bg-blue-100 text-blue-700 border border-blue-300{% endif %}">
        {{ message }}
      </div>
      {% endfor %}
    </div>
    {% endif %}
  {% endwith %}

  <!-- Main content -->
  <main class="max-w-lg mx-auto px-4 pt-4">
    {% block content %}{% endblock %}
  </main>

  <!-- Bottom navigation -->
  {% include '_bottom_nav.html' %}

  {% block scripts %}{% endblock %}
</body>
</html>
```

### 2. Create the bottom navigation bar

`app/templates/_bottom_nav.html`:

```html
{% if current_user.is_authenticated %}
<nav class="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 z-40">
  <div class="max-w-lg mx-auto flex justify-around py-2">
    <a href="{{ url_for('grocery.index') }}"
       class="flex flex-col items-center text-xs
       {% if request.path.startswith('/grocery') %}text-blue-600 font-semibold{% else %}text-gray-500{% endif %}">
      <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
      </svg>
      <span>List</span>
    </a>
    <a href="{{ url_for('favorites.index') }}"
       class="flex flex-col items-center text-xs
       {% if request.path.startswith('/favorites') %}text-blue-600 font-semibold{% else %}text-gray-500{% endif %}">
      <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"/>
      </svg>
      <span>Favorites</span>
    </a>
    <a href="{{ url_for('household.index') }}"
       class="flex flex-col items-center text-xs
       {% if request.path.startswith('/household') %}text-blue-600 font-semibold{% else %}text-gray-500{% endif %}">
      <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-4 0a1 1 0 01-1-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 01-1 1"/>
      </svg>
      <span>Home</span>
    </a>
  </div>
</nav>
{% endif %}
```

### 3. Create reusable macros

`app/templates/_macros.html`:

```html
{% macro render_field(field) %}
<div class="mb-4">
  <label for="{{ field.id }}" class="block text-sm font-medium text-gray-700 mb-1">
    {{ field.label.text }}
  </label>
  {{ field(class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-base", **kwargs) }}
  {% for error in field.errors %}
    <p class="mt-1 text-sm text-red-600">{{ error }}</p>
  {% endfor %}
</div>
{% endmacro %}

{% macro render_button(text, color="blue") %}
<button type="submit"
  class="w-full py-3 px-4 bg-{{ color }}-600 text-white rounded-lg font-medium text-base
         hover:bg-{{ color }}-700 active:bg-{{ color }}-800 transition-colors">
  {{ text }}
</button>
{% endmacro %}
```

### 4. Style the auth templates

Update `app/templates/auth/login.html`, `register.html`, and `join.html` using the macros and Tailwind classes. Each form should be centered, mobile-friendly, with large touch targets (minimum 44px height for buttons and inputs).

### 5. Add HTMX CSRF configuration

Add this script to `base.html` to automatically include the CSRF token with HTMX requests:

```html
<script>
  document.body.addEventListener('htmx:configRequest', function(event) {
    event.detail.headers['X-CSRFToken'] = document.querySelector('meta[name="csrf-token"]').content;
  });
</script>
```

---

## Acceptance Criteria

- [ ] Base template renders with Tailwind classes applied
- [ ] Bottom navigation shows 3 tabs (List, Favorites, Home) with active state highlighting
- [ ] Navigation is fixed to bottom and doesn't scroll with page content
- [ ] Flash messages display at the top with color coding (red for errors, green for success)
- [ ] All forms include CSRF tokens
- [ ] HTMX requests automatically include CSRF token in header
- [ ] Mobile viewport prevents unwanted zoom
- [ ] All input fields have minimum 16px font size (prevents iOS zoom)
