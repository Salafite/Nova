---
name: erp-dynamic-screen
description: Build a new dynamic ERP program screen (browse/maintain grid like BS001) using the shared ErpGrid component stack — one HTML file with a declarative config instead of hand-written markup. ANY record browse/list/maintenance screen MUST be built this way (a single ErpGrid config), never as hand-authored HTML/CSS/JS — even when it needs custom columns, lookups, status pills, or toolbar actions; hand-rolling reintroduces solved theming/form/boot defects. Use when the user asks to create a new program screen, a maintenance/browse screen for a table, a "screen like BS001", a UI for a table API, or to regenerate/fix a program screen under app/templates/ui/. Also use when wiring a screen into navigation and RBAC. DO NOT USE for the shell (Layout.html), login/dashboard pages, backend APIs, or bespoke non-grid screens (dashboards, approval workbenches, process forms — those follow the gen_fc_bespoke.py template family).
---

# erp-dynamic-screen

Build a complete ERP program screen as **one static HTML file containing only an
`ErpGrid({...})` config**. The shared components render everything else: themed
header, toolbar with mask icons, filter bar, grid with pagination/infinite scroll,
sliding Create/Edit/Display/Delete panel, modals, context menus, keyboard
shortcuts, four theme modes, i18n + RTL, locale date/number formats, CSV export,
and lookup-picker mode.

## Authoritative references (read before writing)

1. **`.docs/how-to-build-a-dynamic-screen.md`** — the full guide: complete config
   reference (§4), free behaviors (§5), recipes (§7), pitfalls (§8). Read it
   first; do not guess config options.
2. **`app/templates/ui/_components/screen-template.html`** — the file to copy.
   Its demo config is the BS001 Permissions screen rebuilt dynamically and
   exercises nearly every option.
3. Component sources when the guide is not enough:
   `app/static/js/erp-grid.js` (config contract, host API),
   `app/static/js/erp-toolbar.js` (toolbar config + custom actions).
4. A generated production example: `app/templates/ui/procurement/Goods Receiving/PR021/PR021.html`.

## Procedure

### 1. Derive the config from the backend (never invent field names)

- Read `app/apis/tables/<TABLE>/schemas.py` for field names (lowercase keys),
  types, lengths, and required flags; `router.py` for the API prefix
  (`/<TABLE>API`) and the exact query-param names of List/Search/Update/Delete
  (the PK param only — COMP/BSUN are NOT query params; the server injects them).
- Identify: primary key (e.g. `pmpmid`), soft-delete `ACTV`
  flag, optimistic-lock `CHGN` column, status columns and their vocabularies.
- If a program-level API exists under `app/apis/programs/<CODE>/`, prefer its
  endpoints over raw table CRUD.

### 2. Create the file in the canonical location

`app/templates/ui/<group>/<subgroup>/<PROG>/<PROG>.html` — kebab-case group
folder from the 20-group taxonomy (`Recommended_ERP_Groups_and_Subgroups.md`).
Copy `screen-template.html`, change `<title>`, replace the config. Keep the
inline flash-prevention script and the `boot()`-after-`i18n.init()` pattern
verbatim.

### 3. Write the config

Minimum: `program`, `title`, `table`, `entityName`, `primaryKey`, `api{}`,
`columns[]`, `fields[]`. Add as needed: `filters[]`, `searchFields[]`,
`smartLinks[]`, `toolbar{}` (use `readOnly: true` for inquiries), `buildPayload`
(`parseInt` on select values, audit fields `<p>crid`/`<p>chid`, CHGN pass-through
for updates — see guide §7.4; do NOT set the company column, the server injects it).
For forms with many
fields set `formColumns` (`0` = responsive auto-fill default, `N` = fixed columns,
guide §4.11) — **never build your own form container**; the panel already scrolls
with a pinned Save footer.

For a field that references another table, use a `type: 'lookup'` field — a record
picker that opens another screen (`lookupUrl` + `#S`). To store the foreign key but
**display a friendly name**, add `lookupDisplayField` + `lookupNameMap` (pre-fetch the
key→name map at boot); the key is still what gets submitted. See guide §4.5 and recipe
§7.6 (BS001 Permission → Group is the live example).

### 4. Wire into the application

- **Navigation:** add `{id, label, icon, url}` to
  `app/templates/navigation/NavigationData.json` under the matching
  group/subgroup. Grouping is presentation-only; never change the program code.
- **RBAC:** the program must have MDPROG + COPMST/COPERM/COPMAP rows — extend
  the module's `migrations/seed_<mod>_permissions.py` (idempotent MARKER
  pattern). Without seeds the nav filters the screen out for everyone.
- **i18n (optional, can be deferred):** add `screens.<prog>.*` keys to
  `/static/locales/<lang>.json`; missing keys fall back to literal labels.
- For a whole table family, extend the module's `migrations/gen_<mod>_screens.py`
  generator instead of hand-writing many configs.

### 5. Document the screen (three companion files — required for every screen)

Write these **next to the HTML**, in the same `<PROG>/` folder
(`app/templates/ui/<group>/<subgroup>/<PROG>/`). Copy the skeletons from
`app/templates/ui/_components/screen-doc-templates/` and fill them in; the `BS010/`
folder is a complete worked example. Keep each to one page; derive every fact from
the config and the backend, never invent. (For a whole table family built through
`gen_<mod>_screens.py`, have the generator emit all three per screen.)

- **`readme.md`** — human overview: program code + title, what the screen
  maintains, the backing table + program-API prefix, the navigation path
  (group ▸ subgroup), the RBAC roles that get full vs read access, and how to open
  + verify it in the shell.
- **`design.md`** — design spec: purpose/scope; the config at a glance
  (`primaryKey`, company scoping, toolbar mode, `formColumns`); columns
  (key → label → type); form fields (key → label → type → required); filters +
  search fields; lookups / smart-links; the `buildPayload` field mapping incl.
  the CHGN/optimistic-lock source; and any deliberate deviation from
  `screen-template.html` with its reason.
- **`apis_per_panel.md`** — a table mapping each UI panel/area to the exact
  endpoint(s) it calls and the params/auth each sends: grid/list → `GET
  /<API>/List?...`; header search → `/Search` or `/List?search=`; Create panel →
  `POST /<API>/Create`; Edit panel → `PUT /<API>/Update?...`; Delete confirm →
  `DELETE /<API>/Delete?...`; every lookup field → its picker screen + API; each
  custom toolbar action → its endpoint. Every row must be a route that actually
  exists in `router.py` (this doubles as the rule-13 endpoint audit).

### 6. Verify

Run the nav-vs-disk-vs-MDPROG consistency checker, then walk the checklist in
the guide §9: screen loads in shell, CRUD round-trip, selection-driven toolbar
state, all four themes (icons visible on dark/HC), one RTL language, CSV export,
RBAC allow + deny. Confirm the three companion docs exist and match the shipped
config.

## Hard rules (violations break the screen)

1. Script order: `auth-check.js` first; `erp-toolbar.js` **before**
   `erp-grid.js` (the grid throws otherwise).
2. The theme/direction flash-prevention script stays **inline in `<head>`
   before the CSS links**.
3. **Absolute asset paths only** (`/static/...`) — screens are served from deep
   static URLs.
4. **No Jinja, no shared layout** — screens are served as raw static files, so
   `{% extends "Layout.html" %}` / `{% block %}` are sent to the browser
   verbatim and never render the shell or load any CSS. Each screen is a
   **complete standalone `<!DOCTYPE html>` document**: copy the entire `<head>`
   (flash-prevention script → CSS links → the four ordered `<script>` includes)
   and `<body>` skeleton from `screen-template.html`; replace only `<title>` and
   the config.
5. Field/column `key`s are the **lowercase API names**; `meta.colName` carries
   the uppercase DB column.
6. API responses must be the `{status: 'OK', data: [...]}` envelope; all calls
   go through `window.authFetch`.
7. High-contrast mode = `dark` + `high-contrast` classes together — per-screen
   HC CSS rules must come after dark rules.
8. Never restyle toolbar mask icons with text-color utilities — they are colored
   via `background-color` on `.program-bar-icon` in `erp-grid.css`.
9. `versionField` config exists but is **not consumed** — send CHGN yourself in
   `buildPayload` for optimistic locking.
10. The live shell is `app/templates/Layout.html` (`/home`) —
    `app/designs/code.html` is an unserved duplicate; never edit it.
11. Markup rendered from JS (custom `render` functions, toolbar `actions`)
    must obey the theme system: never set a fixed text color on grid cell
    content — themes recolor `#table-area tbody td` and content must inherit
    (guide pitfall 16) — and only use Tailwind classes that actually exist in
    `dist.css`; otherwise add theme-aware rules to `erp-grid.css` (guide
    pitfall 15 — `bg-primary`, `bg-opacity-*`, and `md:`/`xl:` variants are
    all real casualties).
12. **Constructor takes ONE config object**, mounted with no/optional target:
    `new ErpGrid({ ...config }).mount();` (it appends to `document.body`).
    NEVER `new ErpGrid('#sel', config)` — the selector becomes the config and
    the real config is silently dropped, so the grid renders as an empty
    default `XX000` with no columns or API.
13. **Configure only endpoints that exist — read `router.py` and list every
    `@router.<verb>` first.** Common traps: not every program has a `/Search`
    route (if absent, search is a param on List: `'/List?...&search={term}'`,
    and `{field}` is simply unused); composite-key join tables (e.g. CORLPM
    role↔permission) expose only Create + Delete, so omit `api.update`, set
    `toolbar: { buttons: ['new','display','delete','refresh'] }` (no Edit), and
    for the multi-column delete use the **function form**
    `remove: (row) => '/Delete?...rprlid=${row.rprlid}&rppmid=${row.rppmid}'`
    with a stable `primaryKey` (a backend `@computed_field id` like
    `f"{rprlid}_{rppmid}"`).
14. **COMP/BSUN are server-injected — never put company in the screen.** The backend
    derives company + business unit from the session and enforces them on every
    read/write (`app/core/tenancy.py`; COMP/BSUN tenancy initiative). Do **not** add a
    `company` config key, a `company` function, or a `buildPayload` that sets the
    company column, and do **not** include `?<p>comp=` or the `{company}` placeholder
    in `api` URLs — the server owns the tenant. The grid substitutes `{maxrec}` and
    `{pk}` (`{company}`/`{comp}` are obsolete).

## Already-fixed defects — never reintroduce these

The component stack already solved these screen-level bugs (defect log #11–#18 in
`.docs/tasks.md`, §10 of the guide). They come back **only when a generated screen
deviates from `screen-template.html`** — copy that file verbatim and do not
hand-author chrome, CSS, or boot logic. The three that keep recurring:

- **Broken theming / colors (#14, #17, #18).** Theming is driven entirely by
  `dist.css` + `erp-grid.css`; the template `<head>` already themes the whole
  screen across light / dark / high-contrast / custom. **Do NOT add a per-screen
  `<style>` block, CSS variables (`--app-bg`…), `!important` overrides, or
  hardcoded hex / `text-gray-*` / `bg-*` colors** — that is exactly how dark/HC
  unreadability, invisible primary buttons, and solid-black modal backdrops come
  back. In any `render` / toolbar-`actions` markup, set weight/font/alignment only
  and let cell text inherit `tbody td` (rule 11); use only Tailwind classes that
  exist in `dist.css` (never `bg-opacity-*`, `bg-primary`, `md:`/`xl:` from JS).

- **Cramped / unscrollable forms (#13, #14).** The detail panel already scrolls
  with a pinned Save footer and lays fields out responsively. Never build your own
  form container or set a fixed `max-w-*` width; for many fields use `formColumns`
  (config step 3). Re-implementing the form is what brings back the narrow
  single-column strip and the off-screen Save button.

- **Blank screen / logout (#11, #13).** Almost never the config data — it is a
  deviation from the template's boot path. Keep all four intact:
  1. `boot()` wrapped in `i18n.init().then(boot, boot)` (removing it brings back
     the i18n null-key crash and the RTL/English flash).
  2. `auth-check.js` loaded from `/ui/assets/js/auth-check.js` — **not**
     `/static/js/auth-check.js` (a 404 here = no `authFetch` = blank grid).
  3. Instantiate with `new ErpGrid({...}).mount()` (rule 12).
  4. Every `api` endpoint exists in `router.py` and returns `{status:'OK',
     data:[...]}` — a single 401 ejects the **whole shell** to login (rule 13).

## Success criteria

A new screen is done when it renders inside the shell with working
List/Create/Update/Delete against the real API, is reachable in navigation for
an authorized role and hidden for an unauthorized one, passes the consistency
checker, renders correctly in light, dark, high-contrast, custom theme, and one
RTL language, and ships with its three companion docs (`readme.md`, `design.md`,
`apis_per_panel.md`) in the program folder.
