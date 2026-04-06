# Ticket 10: Grocery List Page — Main UI

**Phase:** 3 — Frontend & UI  
**Priority:** Critical  
**Dependencies:** Ticket 9, Ticket 5  
**Estimated effort:** Medium

---

## Why This Matters

This is the page users open every day. It must be fast, clean, and finger-friendly on a phone. The layout has four sections: search/add at the top, favorite quick-add buttons, active items, and checked items with a confirm button.

## Reference

- UI spec: `Schema_API_UI_sub_specs.md` sections 3.2–3.5
- HTMX behavior: `Route_Contract.md` section 7

---

## Tasks

### 1. Build the main grocery page template

`app/templates/grocery/index.html`:

```html
{% extends "base.html" %}
{% block title %}Grocery List{% endblock %}

{% block content %}
<!-- Add item form with search -->
<section class="mb-4">
  <form hx-post="{{ url_for('grocery.add_item') }}"
        hx-target="#grocery-list"
        hx-swap="innerHTML"
        class="space-y-2">
    {{ form.hidden_tag() }}
    <div class="relative">
      {{ form.name(
        placeholder="Add item...",
        class="w-full p-4 text-lg border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500",
        autocomplete="off",
        **{"hx-get": url_for('grocery.search'),
           "hx-trigger": "keyup changed delay:300ms",
           "hx-target": "#search-results",
           "hx-swap": "innerHTML",
           "name": "name"}
      ) }}
      <div id="search-results"
           class="absolute left-0 right-0 bg-white border border-gray-200 rounded-b-lg shadow-lg z-10 hidden">
      </div>
    </div>
    <div class="flex gap-2">
      {{ form.quantity(placeholder="Qty", class="w-20 p-3 border border-gray-300 rounded-lg text-base") }}
      {{ form.unit(placeholder="Unit", class="flex-1 p-3 border border-gray-300 rounded-lg text-base") }}
      {{ form.note(placeholder="Note", class="flex-1 p-3 border border-gray-300 rounded-lg text-base") }}
    </div>
    <button type="submit"
            class="w-full py-3 bg-blue-600 text-white rounded-lg font-medium text-lg
                   active:bg-blue-800 transition-colors">
      Add Item
    </button>
  </form>
</section>

<!-- Favorite quick-add buttons -->
{% if favorites %}
<section class="mb-4 flex gap-2 overflow-x-auto pb-2">
  {% for fav in favorites %}
  <button hx-post="{{ url_for('favorites.quick_add', favorite_id=fav.id) }}"
          hx-target="#grocery-list"
          hx-swap="innerHTML"
          class="flex-shrink-0 px-4 py-2 bg-blue-100 text-blue-800 rounded-full text-sm
                 font-medium whitespace-nowrap active:bg-blue-200 transition-colors">
    {{ fav.name }}
  </button>
  {% endfor %}
</section>
{% endif %}

<!-- Grocery list (HTMX target) -->
<div id="grocery-list"
     hx-get="{{ url_for('grocery.fragment_list') }}"
     hx-trigger="every 15s"
     hx-swap="innerHTML">
  {% include 'grocery/_list.html' %}
</div>
{% endblock %}
```

### 2. Build the list fragment template

`app/templates/grocery/_list.html`:

```html
<!-- Active items -->
<section id="active-items" class="mb-4">
  <h2 class="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
    To Buy ({{ active_items|length }})
  </h2>
  {% if active_items %}
    {% for item in active_items %}
      {% include 'grocery/_item_row.html' %}
    {% endfor %}
  {% else %}
    <p class="text-gray-400 text-center py-8">No items yet. Add something above!</p>
  {% endif %}
</section>

<!-- Checked items -->
{% if checked_items %}
<section id="checked-items-container" class="mb-4">
  <h2 class="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
    Done ({{ checked_items|length }})
  </h2>
  {% include 'grocery/_checked_list.html' %}

  <!-- Confirm purchase button -->
  <button hx-post="{{ url_for('grocery.confirm') }}"
          hx-target="#checked-items-container"
          hx-swap="innerHTML"
          hx-confirm="Remove all checked items?"
          class="w-full mt-3 py-3 bg-green-600 text-white rounded-lg font-medium text-base
                 active:bg-green-800 transition-colors">
    Confirm Purchase ({{ checked_items|length }})
  </button>
</section>
{% endif %}
```

### 3. Build the item row fragment

`app/templates/grocery/_item_row.html`:

```html
<div hx-post="{{ url_for('grocery.toggle', item_id=item.id) }}"
     hx-target="this"
     hx-swap="outerHTML"
     class="flex items-center justify-between p-4 border-b border-gray-100 cursor-pointer
            {% if item.status == 'checked' %}bg-gray-50{% else %}bg-white active:bg-gray-50{% endif %}
            transition-colors">
  <div class="flex items-center gap-3 flex-1 min-w-0">
    <div class="w-6 h-6 rounded-full border-2 flex items-center justify-center flex-shrink-0
                {% if item.status == 'checked' %}border-green-500 bg-green-500{% else %}border-gray-300{% endif %}">
      {% if item.status == 'checked' %}
        <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"/>
        </svg>
      {% endif %}
    </div>
    <div class="flex-1 min-w-0">
      <p class="text-base truncate
                {% if item.status == 'checked' %}line-through text-gray-400{% else %}text-gray-900{% endif %}">
        {{ item.name }}
      </p>
      {% if item.note %}
      <p class="text-xs text-gray-400 truncate">{{ item.note }}</p>
      {% endif %}
    </div>
  </div>
  <div class="text-right flex-shrink-0 ml-2
              {% if item.status == 'checked' %}text-gray-400{% else %}text-gray-600{% endif %}">
    <span class="text-sm font-medium">{{ item.quantity_value }}{% if item.unit %} {{ item.unit }}{% endif %}</span>
  </div>
</div>
```

### 4. Build the checked list and search results fragments

`app/templates/grocery/_checked_list.html`:

```html
{% for item in checked_items %}
  {% include 'grocery/_item_row.html' %}
{% endfor %}
```

`app/templates/grocery/_search_results.html`:

```html
{% if results and (results.favorites or results.history) %}
<ul class="py-1">
  {% for fav in results.favorites %}
  <li class="px-4 py-3 hover:bg-gray-50 cursor-pointer border-b border-gray-100 text-base"
      onclick="document.querySelector('[name=name]').value='{{ fav.name }}'; document.getElementById('search-results').classList.add('hidden')">
    <span class="text-yellow-500 mr-1">★</span> {{ fav.name }}
    {% if fav.default_unit %}({{ fav.default_unit }}){% endif %}
  </li>
  {% endfor %}
  {% for name in results.history %}
  <li class="px-4 py-3 hover:bg-gray-50 cursor-pointer border-b border-gray-100 text-base"
      onclick="document.querySelector('[name=name]').value='{{ name }}'; document.getElementById('search-results').classList.add('hidden')">
    {{ name }}
  </li>
  {% endfor %}
</ul>
{% endif %}
```

### 5. Add JavaScript for search dropdown visibility

Add to `base.html` or a separate JS file:

```html
<script>
  document.addEventListener('htmx:afterSwap', function(event) {
    if (event.detail.target.id === 'search-results') {
      const el = event.detail.target;
      el.classList.toggle('hidden', el.innerHTML.trim() === '');
    }
  });
  document.addEventListener('click', function(event) {
    const sr = document.getElementById('search-results');
    if (sr && !sr.contains(event.target)) {
      sr.classList.add('hidden');
    }
  });
</script>
```

### UI Component Reference

| Component | Tailwind Classes |
|-----------|-----------------|
| Search input | `w-full p-4 text-lg border rounded-lg` |
| Favorite button | `px-3 py-2 bg-blue-100 rounded text-sm` |
| Active item | `p-4 border-b flex justify-between bg-white` |
| Checked item | `p-4 border-b line-through text-gray-400 bg-gray-50` |
| Confirm button | `fixed bottom-16 w-full p-4 bg-green-500 text-white` |

---

## Acceptance Criteria

- [ ] Grocery page loads with all sections visible on mobile
- [ ] Typing in the search field triggers live suggestions after 300ms
- [ ] Selecting a suggestion fills the item name field
- [ ] Submitting the form adds the item and refreshes the list (no full page reload with HTMX)
- [ ] Tapping an item row toggles its checked/active state
- [ ] Active items show with clear styling; checked items show with strikethrough and grey
- [ ] "Confirm Purchase" button only appears when checked items exist
- [ ] Confirm shows a confirmation dialog before executing
- [ ] Favorite quick-add buttons are scrollable horizontally
- [ ] All touch targets are at least 44px tall
- [ ] The page auto-refreshes the list every 15 seconds via HTMX polling
