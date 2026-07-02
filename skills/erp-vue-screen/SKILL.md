---
name: erp-vue-screen
description: Build a new Vue 3 ERP screen (browse/maintain) using the project's existing Vue patterns — Pinia stores, axios API client, Vue Router with hash history, and AppLayout shell. For each screen, first analyze the backend (CAG pass) to derive the data contract, then build the Vue view, and finally generate three documentation files (README.md, api-used.md, fields.md). Use when the user asks to create a new program screen for a backend table, a CRUD interface for an API endpoint, or to migrate a legacy template screen to Vue. DO NOT USE for standalone pages (login, dashboard, shell) that don't follow the grid/browse pattern.
---

# erp-vue-screen

Build a complete ERP screen as a **Vue 3 Single-File Component** that follows the project's existing patterns: axios API client with Bearer auth, Pinia Options API stores, Vue Router hash-based routing, and the AppLayout shell (sidebar or grid topbar). Every screen ships with **three companion documentation files**.

## Authoritative references (read before writing)

1. **Existing completed screen** — `apps/web-vue/src/views/settings/SettingsView.vue` is the most feature-complete Vue screen. Use it as a reference for: loading state, error state, empty state, dirty tracking, save patterns, toast feedback, and reactive search.
2. **API client** — `apps/web-vue/src/api/client.js` — how to make authenticated API calls (always use the `api` export, never bare `fetch`).
3. **Router** — `apps/web-vue/src/router/index.js` — route naming (lowercase kebab), component lazy loading, auth guard.
4. **Store pattern** — `apps/web-vue/src/stores/auth.js`, `stores/settings.js` — Pinia Options API: `state`, `getters`, `actions` shape.
5. **Layout** — `apps/web-vue/src/layouts/AppLayout.vue` — how the shell renders sidebar vs grid-topbar, toast container, full-width content.
6. **Toast composable** — `apps/web-vue/src/composables/useToast.js` — module-scoped reactive toasts, `show(message, type)`.
7. **Backend controller pattern** — `modules/*/controllers/T*I.py` — the API prefix is `/api/TXXXXI`, the `response_model` is the Pydantic response class.
8. **Backend model pattern** — `modules/*/models/*.py` — `*Create`, `*Update` (all Optional fields), `*Response(AuditMixin)`.
9. **Backend service pattern** — `modules/*/services/*.py` — extends `CrudService`, adds domain methods, never contains HTTP or SQL.
10. **i18n composable** — `apps/web-vue/src/composables/useI18n.js` — provides `{ locale, dir, isRTL, t }` that reactively reads `SYSTEM_LANGUAGE` from the settings store. `dir` is auto-applied to `<html>`. Use `t(key)` for all user-facing strings — it returns Arabic when `SYSTEM_LANGUAGE` is `ar-EG` and English otherwise. Add new keys to the shared `dict` object inside the composable. Switching the setting in `SettingsView` propagates instantly to all screens with zero page reload.

## Procedure

### 1. CAG pass — Analyze the backend first (never invent fields or endpoints)

Before writing any UI code, read the following backend files to derive the **exact** data contract:

- **Model file** (`modules/<module>/models/<table>.py`): extract every field name, type, whether it's optional/required, and the response model shape.
- **Controller file** (`modules/<module>/controllers/T*I.py`): extract every API endpoint, HTTP method, URL prefix, path params, query params, and request body schema.
- **Service file** (`modules/<module>/services/<service>.py`): extract domain-specific methods (e.g. `get_by_group`, `bulk_update`) that expose non-standard endpoints.
- **Repository instantiation** (in the controller): extract the `business_columns` list — these are the exact DB column names the screen must handle.

If the backend does not exist for a table, first build it following Clean Architecture:

```
controller (thin, HTTP only) → service (business logic) → repository (SQL only)
```

### 2. Create the Vue view

```
apps/web-vue/src/views/<feature>/<Name>View.vue
```

#### Minimum template structure

Always use `t('key')` instead of hardcoded English text. The `t()` function returns Arabic when SYSTEM_LANGUAGE is `ar`, English otherwise. Add any new keys to the `dict` inside `composables/useI18n.js`.

```vue
<template>
  <div :dir="dir">
    <!-- Header row: title + action button(s) -->
    <div class="flex justify-between items-center mb-6">
      <div>
        <h2 class="page-title">{{ t('screen-title', 'Screen Title') }}</h2>
        <p class="page-subtitle">{{ t('screen-sub', 'Screen description') }}</p>
      </div>
      <button class="btn-primary" @click="openAdd">{{ t('add-new') }}</button>
    </div>

    <!-- Loading / Error / Empty states -->
    <div v-if="loading" class="loading-state">{{ t('loading') }}</div>
    <div v-else-if="error" class="error-state">{{ error }}</div>
    <div v-else-if="!items.length" class="empty-state">{{ t('no-records') }}</div>

    <!-- Data table -->
    <div v-else class="data-card">
      <table class="data-table">
        <thead>
          <tr>
            <th>{{ t('code') }}</th>
            <th>{{ t('name') }}</th>
            <th>{{ t('status') }}</th>
            <th class="text-center">{{ t('actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in items" :key="item.id">
            <td>{{ item.field }}</td>
            <td>
              <span v-if="item.is_active" class="badge badge-active">{{ t('active') }}</span>
              <span v-else class="badge badge-inactive">{{ t('inactive') }}</span>
            </td>
            <td class="text-center">
              <button class="btn-icon" @click="editItem(item)" :title="t('edit')">
                <span class="material-symbols-outlined">edit</span>
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
```

For bilingual data fields that have `_en`/`_ar` variants in the backend model, display the correct variant:

```vue
<td>{{ locale === 'ar-EG' ? item.field_ar : item.field_en }}</td>
```

#### Script pattern (always use `<script setup>`)

Always import `useI18n` and destructure `{ t, dir }`. Use `t('key', 'fallback')` for every user-facing string. When the key does not exist in the dictionary yet, add it inside `composables/useI18n.js`.

```vue
<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../../api/client.js'
import { useToast } from '../../composables/useToast.js'
import { useI18n } from '../../composables/useI18n.js'

const { show: toast } = useToast()
const { t, dir } = useI18n()
const loading = ref(true)
const error = ref('')
const items = ref([])

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get('/TXXXXI/')
    items.value = res.data || []
  } catch {
    error.value = t('failed-load')
    toast(t('failed-load'), 'error')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
```

#### Conventions to follow

- **API calls**: always use `api.get`/`api.put`/`api.post`/`api.delete` from `../../api/client.js`. Never use bare `fetch`. The `api` instance has the auth interceptor built in.
- **Route name**: matches the `module` key in `NavigationData.json`, lowercase. Register in `router/index.js` as a child of `/`.
- **Store**: if the screen needs shared state (settings, preferences), create a Pinia store at `stores/<feature>.js`. Use Options API (`defineStore` with `state/getters/actions`).
- **Toast**: use `useToast()` composable. Message + type (`'success'`, `'error'`, `'info'`).
- **Loading state**: show a centered text "Loading..." or skeleton.
- **Error state**: show the error message in red, with a retry button.
- **Empty state**: show "No records found" with an icon.
- **Status badges**: use `inline-flex px-2 py-1 rounded-full text-xs font-semibold` with color classes (`bg-green-100 text-green-700` for active, `bg-gray-100 text-gray-500` for inactive).
- **Responsiveness**: use `overflow-x-auto` on tables, `flex-wrap` on header rows.
- **No jQuery, no DOM manipulation**: use Vue template refs (`ref` attribute) and `scrollIntoView` instead of `document.getElementById`.
- **No global `window.app`**: use composables and stores.
- **No inline styles**: all styling in `<style scoped>` blocks.
- **Bilingual via `t()`**: every user-facing string must use `t('key')`. Add the key to the `dict` in `composables/useI18n.js` with both `en` and `ar` translations. Never hardcode English text. The `t()` function also accepts a fallback: `t('new-key', 'English Fallback')`.
- **`dir` attribute**: always put `:dir="dir"` on the root element of the template. The global `dir` on `<html>` is auto-managed by `useI18n()` — do not set it manually.
- **RTL layout overrides**: add `[dir="rtl"]` prefixed CSS rules in `<style scoped>` for any screen-specific layout flips (e.g., `[dir="rtl"] .table-header { text-align: right; }`, `[dir="rtl"] .form-row { flex-direction: row-reverse; }`).
- **Bilingual data fields**: for model fields that have `_en`/`_ar` variants (e.g. `name_en`, `name_ar`), display the correct one with `locale === 'ar-EG' ? item.name_ar : item.name_en`.
- **Language in forms**: when creating/editing records that have language variants, provide separate inputs for both `field_en` and `field_ar` in the modal form.

### 3. Wire into the application

- **Router** — add a lazy-loaded child route in `apps/web-vue/src/router/index.js`:
  ```js
  { path: '<feature>', name: '<feature>', component: () => import('../views/<feature>/<Name>View.vue') }
  ```
- **Navigation** — the `navStore` loads from `/NavigationData.json` at runtime. If the JSON does not include the new module, the fallback items in `stores/nav.js` need an entry:
  ```js
  { id: '<feature>', icon: '<material-icon>', label: '<Label>', label_ar: '<Arabic Label>', module: '<feature>' }
  ```
- **Nav section** — place the entry under the matching section (`Foundation`, `CRM & Procurement`, `Administration`, etc.) in the fallback array. Include `label_ar` for Arabic display in sidebar and grid-topbar.
- **Section headers** — sections in the fallback array also need `section_ar`:
  ```js
  { section: 'Foundation', section_ar: 'أساسيات' }
  ```

### 4. Generate the three companion documentation files

Write these next to the Vue view, in the same `views/<feature>/` folder. Every fact must be derived from the backend and the component — never invented.

#### `README.md` — Screen overview

```
# <Screen Title>

**Program code:** `<Table>` (`TXXXX`)

## Purpose
One paragraph describing what this screen does, who uses it, and what business process it supports.

## How to access
1. Log in to Nova ERP
2. Navigate to **<Section> > <Feature>** in the sidebar (or grid topbar)
3. The screen loads at `#/<route-name>`

## Backing table
`Nova.<Table>` — stores all `<entity>` records.

## API prefix
`/api/TXXXXI`

## Permissions
- **Full access**: <role> (can create, edit, delete)
- **Read only**: <role> (can view only)

## Dependencies
- Depends on: <related table/feature>
- Used by: <features that consume this data>
```

#### `api-used.md` — API endpoints used

```
# API Endpoints — <Screen Title>

| # | Method | Endpoint | Purpose | Request | Response |
|---|--------|----------|---------|---------|----------|
| 1 | GET | `/api/TXXXXI/` | List all records | — | `SettingResponse[]` |
| 2 | GET | `/api/TXXXXI/{id}` | Get single record | `id` (path) | `SettingResponse` |
| 3 | POST | `/api/TXXXXI/` | Create record | `*Create` body | `*Response` |
| 4 | PUT | `/api/TXXXXI/{id}` | Update record | `id` (path) + `*Update` body | `*Response` |
| 5 | DELETE | `/api/TXXXXI/{id}` | Delete record | `id` (path) | 204 |

**Auth:** All endpoints require `Bearer` token (attached automatically by `api` client).

**Base URL:** `http://localhost:8070/api`
```

For screens with custom endpoints (e.g. `/by-group/summary`, `/bulk`), add rows for those.

#### `fields.md` — Field definitions

```
# Fields — <Screen Title>

## Database columns (`Nova.<Table>`)

| Column | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| id | `SERIAL` | Yes | auto | Primary key |
| <field> | `<type>` | Yes/No | `<default>` | <description> |
| is_active | `BOOLEAN` | No | `TRUE` | Soft-delete flag |
| created_at | `TIMESTAMPTZ` | No | `now()` | Audit |
| updated_at | `TIMESTAMPTZ` | No | `now()` | Audit |
| update_number | `INT` | No | `1` | Optimistic lock |

## Pydantic models

### `<Entity>Create`
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| <field> | `<type>` | Yes/No | <notes> |

### `<Entity>Update`
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| <field> | `<type>` | No | All fields Optional for partial update |

### `<Entity>Response`
Extends `AuditMixin` — adds `created_at`, `created_by`, `updated_at`, `updated_by`, `update_number`.
```

### 5. Verify

1. Run `npx vite build` — must pass with zero errors.
2. Confirm the screen loads in the browser at `#/<route-name>`.
3. Confirm the API endpoint returns real data (not hardcoded mocks).
4. Confirm all three doc files exist at `views/<feature>/README.md`, `api-used.md`, `fields.md`.
5. Confirm the route is accessible after login and redirects to `/login` when unauthenticated.

## Hard rules (violations cause defects)

1. **Never use `fetch` directly** — always use the `api` axios instance from `api/client.js`. Bare fetch does not have auth or 401 handling.
2. **Never use `document.getElementById`** — use Vue template refs (`ref` attribute + `ref()` variable).
3. **Never use `window.app`** — use composables (`useToast`, `useSettingsUI`) or Pinia stores.
4. **No inline `<style>` on elements** — all styles in `<style scoped>`.
5. **No hardcoded mock data** in production code — if the API is unavailable, show an error state, not fake rows.
6. **Three states always rendered** — loading, error, empty (plus the data state). Never assume data exists.
7. **Route name matches nav module key** — the `name` in `router/index.js` must match the `module` value in nav items.
8. **Every endpoint in `api-used.md` must exist** in the controller — read the controller's route definitions, don't guess.
9. **Every field in `fields.md` must match** the Pydantic model — read the model file, don't guess.
10. **Swallowed errors get a toast** — every `catch` block must show a user-visible message via `toast()`.
11. **Every screen must use `t()` for all user-facing strings** — import `const { t, dir } = useI18n()` at the top of every component. Every text node, button label, placeholder, title attribute, column header, and toast message must use `t('key')` or `t('key', 'Fallback')`. Hardcoded English text (except `{{ error }}` which comes from the API) is a defect. Add new translation keys to the `dict` inside `composables/useI18n.js`.

## Already-solved patterns — never reintroduce

- **`window.app.toast`** (removed from `main.js`) — use `useToast()` composable instead.
- **`document.getElementById`** in AppLayout/SettingsView (replaced with template refs) — use `ref` + `scrollIntoView`.
- **Inline `fetch` with manual auth headers** — the `api` axios instance handles Bearer token and 401 redirect globally.
- **Hardcoded setting key lists** in the view (e.g., `TOGGLE_KEYS`) — extracted into a composable (`useSettingsUI`).
- **Inline `locale === 'ar-EG' ?` for every label** — replaced by `t('key')` which reads from a shared dictionary in `useI18n.js`. Add new keys to `dict` once; all screens share the same translations.
- **Hardcoded English nav labels** — replaced by `label_ar` / `section_ar` fields on nav items. Sidebar and grid-topbar show the right language reactively.

## Success criteria

A new screen is done when:
- It loads data from the real API endpoint and renders it in a table/grid.
- Loading, error, and empty states are handled.
- Create/Update/Delete work (if applicable) with toast feedback.
- The route is registered and accessible via sidebar navigation.
- `npx vite build` passes with zero errors.
- `README.md`, `api-used.md`, and `fields.md` exist in the view folder with facts verified against the backend.
- Every user-facing string uses `t('key')` — no hardcoded English text. The `dir` attribute is applied on the root element. Switching SYSTEM_LANGUAGE in Settings instantly flips all labels and layout direction without a page reload.
