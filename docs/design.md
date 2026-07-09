---
version: alpha
name: Nova Design System
description: Design system for Nova ERP, an open-source ERP for small F&B distributors

colors:
  primary: "#5d3fd3"
  primary-hover: "#4a32b0"
  primary-faded: "#e6deff"
  on-primary: "#ffffff"
  surface: "#ffffff"
  surface-low: "#f9fafb"
  surface-hover: "#f5f5f5"
  body: "#f5f5f9"
  on-surface: "#1a1a2e"
  on-surface-secondary: "#333333"
  on-surface-muted: "#666666"
  on-surface-subtle: "#767676"
  on-surface-faint: "#999999"
  border-default: "#e0e0e0"
  border-light: "#f0f0f0"
  border-input: "#dddddd"
  sidebar-bg: "#1a1a2e"
  sidebar-text: "#cccccc"
  sidebar-active: "#cabeff"
  error: "#dc2626"
  success: "#16a34a"
  warning: "#d97706"
  info: "#0284c7"
  error-bg: "#fee2e2"
  success-bg: "#dcfce7"
  warning-bg: "#fef3c7"
  info-bg: "#e0f2fe"
  disabled-bg: "#f0f0f2"
  disabled-text: "#b3b3bd"
  focus-ring: "#5d3fd3"
  shadow-card: "0 1px 3px rgba(0,0,0,0.05)"

colors-dark:
  primary: "#cabeff"
  primary-hover: "#b8a0ff"
  primary-faded: "#2a1a5e"
  on-primary: "#1a1a2e"
  surface: "#1a1a2e"
  surface-low: "#222240"
  surface-hover: "#2a2a4a"
  body: "#0f0f1a"
  on-surface: "#e8e8f0"
  on-surface-secondary: "#ccccdd"
  on-surface-muted: "#9999aa"
  on-surface-subtle: "#8888a0"
  on-surface-faint: "#666677"
  border-default: "#2a2a4a"
  border-light: "#222240"
  border-input: "#3a3a5a"
  sidebar-bg: "#0a0a18"
  sidebar-text: "#9999aa"
  sidebar-active: "#cabeff"
  disabled-bg: "#22223a"
  disabled-text: "#4a4a60"
  focus-ring: "#cabeff"
  shadow-card: "0 1px 3px rgba(0,0,0,0.2)"

typography:
  fontFamily:
    latin: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    arabic: "'Noto Sans Arabic', 'Tahoma', sans-serif"
    mono: "'JetBrains Mono', 'Courier New', monospace"
  display:
    fontFamily: "{typography.fontFamily.latin}"
    fontFamilyAr: "{typography.fontFamily.arabic}"
    fontSize: 40px
    fontWeight: 800
    lineHeight: 1.2
  h1:
    fontFamily: "{typography.fontFamily.latin}"
    fontFamilyAr: "{typography.fontFamily.arabic}"
    fontSize: 22px
    fontWeight: 700
    lineHeight: 1.3
  h2:
    fontFamily: "{typography.fontFamily.latin}"
    fontFamilyAr: "{typography.fontFamily.arabic}"
    fontSize: 28px
    fontWeight: 700
    lineHeight: 1.3
  h3:
    fontFamily: "{typography.fontFamily.latin}"
    fontFamilyAr: "{typography.fontFamily.arabic}"
    fontSize: 16px
    fontWeight: 700
    lineHeight: 1.4
  card-title:
    fontFamily: "{typography.fontFamily.latin}"
    fontFamilyAr: "{typography.fontFamily.arabic}"
    fontSize: 14px
    fontWeight: 700
    lineHeight: 1.4
  subtitle:
    fontFamily: "{typography.fontFamily.latin}"
    fontFamilyAr: "{typography.fontFamily.arabic}"
    fontSize: 13px
    fontWeight: 400
    lineHeight: 1.5
  body:
    fontFamily: "{typography.fontFamily.latin}"
    fontFamilyAr: "{typography.fontFamily.arabic}"
    fontSize: 13px
    fontWeight: 400
    lineHeight: 1.5
  button:
    fontFamily: "{typography.fontFamily.latin}"
    fontFamilyAr: "{typography.fontFamily.arabic}"
    fontSize: 13px
    fontWeight: 600
    lineHeight: 1
  table-header:
    fontFamily: "{typography.fontFamily.latin}"
    fontFamilyAr: "{typography.fontFamily.arabic}"
    fontSize: 11px
    fontWeight: 700
    lineHeight: 1
    letterSpacing: 0.5px
  badge:
    fontFamily: "{typography.fontFamily.latin}"
    fontFamilyAr: "{typography.fontFamily.arabic}"
    fontSize: 11px
    fontWeight: 600
    lineHeight: 1
  caption:
    fontFamily: "{typography.fontFamily.latin}"
    fontFamilyAr: "{typography.fontFamily.arabic}"
    fontSize: 12px
    fontWeight: 400
    lineHeight: 1.4
  mono:
    fontFamily: "{typography.fontFamily.mono}"
    fontSize: 12px
    fontWeight: 600
    lineHeight: 1.4

rounded:
  none: 0
  sm: 4px
  md: 6px
  lg: 8px
  xl: 12px
  full: 9999px

zIndex:
  dropdown: 10
  stickyHeader: 20
  overlay: 100
  modal: 101
  toast: 200
  tooltip: 300

spacing:
  0: 0
  1: 4px
  2: 8px
  3: 12px
  4: 14px
  5: 16px
  6: 20px
  7: 24px
  8: 32px
  9: 40px
  10: 48px
  11: 80px

components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.button}"
    rounded: "{rounded.lg}"
    padding: "{spacing.2} {spacing.6}"
    minHeight: 44px
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
    textColor: "{colors.on-primary}"
  button-outline:
    backgroundColor: transparent
    textColor: "{colors.on-surface-secondary}"
    border: "1px solid {colors.border-input}"
    typography: "{typography.button}"
    rounded: "{rounded.lg}"
    padding: "{spacing.2} {spacing.6}"
    minHeight: 44px
  button-outline-hover:
    backgroundColor: "{colors.surface-hover}"
  button-secondary:
    backgroundColor: "{colors.surface-hover}"
    textColor: "{colors.on-surface-secondary}"
    typography: "{typography.button}"
    rounded: "{rounded.lg}"
    padding: "{spacing.2} {spacing.6}"
    minHeight: 44px
  button-secondary-hover:
    backgroundColor: "{colors.border-default}"
  button-icon:
    backgroundColor: transparent
    textColor: "{colors.on-surface-subtle}"
    rounded: "{rounded.md}"
    width: 36px
    height: 36px
  button-icon-hover:
    backgroundColor: "{colors.surface-hover}"
    textColor: "{colors.primary}"
  button-icon-danger:
    backgroundColor: transparent
    textColor: "{colors.on-surface-subtle}"
    rounded: "{rounded.md}"
    width: 36px
    height: 36px
  button-icon-danger-hover:
    backgroundColor: "{colors.error-bg}"
    textColor: "{colors.error}"
  button-sm:
    padding: "{spacing.1} {spacing.5}"
    fontSize: 13px
  button-xs:
    padding: "4px {spacing.3}"
    fontSize: 12px
  form-input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface}"
    border: "1px solid {colors.border-input}"
    rounded: "{rounded.md}"
    padding: "{spacing.2} {spacing.2}"
    fontSize: 13px
  form-input-sm:
    padding: "6px 8px"
    fontSize: 12px
  form-label:
    typography: "{typography.caption}"
    fontWeight: 600
    color: "{colors.on-surface-secondary}"
    marginBottom: 4px
  select:
    appearance: auto
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface}"
    border: "1px solid {colors.border-input}"
    rounded: "{rounded.md}"
    padding: "{spacing.2} {spacing.2}"
    fontSize: 13px
  data-card:
    backgroundColor: "{colors.surface}"
    border: "1px solid {colors.border-default}"
    rounded: "{rounded.xl}"
    overflow: hidden
  data-table:
    width: "100%"
    borderCollapse: collapse
  data-table-header:
    backgroundColor: "{colors.surface-low}"
    typography: "{typography.table-header}"
    color: "{colors.on-surface-muted}"
    padding: "{spacing.2} {spacing.6}"
    borderBottom: "1px solid {colors.border-default}"
  data-table-cell:
    typography: "{typography.body}"
    color: "{colors.on-surface}"
    padding: "{spacing.3} {spacing.6}"
    borderBottom: "1px solid {colors.border-light}"
  data-table-row-hover:
    backgroundColor: "{colors.surface-hover}"
  modal-overlay:
    backgroundColor: "rgba(0,0,0,0.4)"
  modal-content:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.xl}"
    width: 580px
    maxHeight: "85vh"
  modal-content-sm:
    width: 420px
  modal-header:
    padding: "18px 24px"
    borderBottom: "1px solid {colors.border-default}"
  modal-body:
    padding: "24px"
  modal-footer:
    padding: "16px 20px"
    borderTop: "1px solid {colors.border-default}"
  toast:
    backgroundColor: "#333333"
    textColor: "#ffffff"
    rounded: "{rounded.lg}"
    padding: "{spacing.3} {spacing.6}"
    fontSize: 14px
  toast-success:
    backgroundColor: "#00897b"
  toast-error:
    backgroundColor: "#c62828"
  toast-info:
    backgroundColor: "#1565c0"
  badge:
    padding: "3px 10px"
    rounded: "{rounded.full}"
    typography: "{typography.badge}"
  badge-active:
    backgroundColor: "{colors.success-bg}"
    color: "{colors.success}"
  badge-danger:
    backgroundColor: "{colors.error-bg}"
    color: "{colors.error}"
  badge-warning:
    backgroundColor: "{colors.warning-bg}"
    color: "{colors.warning}"
  badge-info:
    backgroundColor: "{colors.info-bg}"
    color: "{colors.info}"
  badge-inactive:
    backgroundColor: "{colors.surface-low}"
    color: "{colors.on-surface-subtle}"
  badge-disabled:
    backgroundColor: "{colors.surface-hover}"
    color: "{colors.on-surface-faint}"
  sidebar:
    backgroundColor: "{colors.sidebar-bg}"
    width: 240px
    collapsedWidth: 64px
  sidebar-item:
    textColor: "{colors.sidebar-text}"
  sidebar-item-active:
    borderLeft: "3px solid {colors.primary}"
    textColor: "{colors.sidebar-active}"
  topbar:
    backgroundColor: "{colors.sidebar-bg}"
    height: 56px
    zIndex: "{zIndex.stickyHeader}"
  topbar-item:
    textColor: "{colors.sidebar-text}"
    typography: "{typography.button}"
    padding: "{spacing.2} {spacing.4}"
  topbar-item-active:
    textColor: "{colors.sidebar-active}"
    borderBottom: "2px solid {colors.primary}"
  module-switcher-trigger:
    width: 40px
    height: 40px
    rounded: "{rounded.md}"
    textColor: "{colors.sidebar-text}"
  module-switcher-panel:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.xl}"
    boxShadow: "{shadowModal}"
    padding: "{spacing.5}"
    width: 360px
  module-tile:
    rounded: "{rounded.lg}"
    padding: "{spacing.5} {spacing.3}"
    textColor: "{colors.on-surface-secondary}"
    hoverBackgroundColor: "{colors.surface-hover}"
  module-tile-active:
    backgroundColor: "{colors.primary-faded}"
    textColor: "{colors.primary}"
  module-subnav:
    backgroundColor: "{colors.surface}"
    borderBottom: "1px solid {colors.border-default}"
    height: 44px
  page-header:
    marginBottom: "{spacing.7}"
  page-title:
    typography: "{typography.h1}"
  page-subtitle:
    typography: "{typography.subtitle}"
    color: "{colors.on-surface-subtle}"
    marginTop: 4px
  empty-state:
    padding: "{spacing.10} {spacing.7}"
    textColor: "{colors.on-surface-faint}"
    fontSize: 14px
  skeleton:
    rounded: "{rounded.sm}"
  toggle-switch:
    width: 44px
    height: 24px
    rounded: "{rounded.full}"
  toggle-slider-active:
    backgroundColor: "{colors.primary}"
  checkbox:
    width: 16px
    height: 16px
    accentColor: "{colors.primary}"
  focus-ring:
    outline: "2px solid {colors.focus-ring}"
    outlineOffset: 2px
  button-disabled:
    backgroundColor: "{colors.disabled-bg}"
    textColor: "{colors.disabled-text}"
    cursor: not-allowed
  input-disabled:
    backgroundColor: "{colors.disabled-bg}"
    textColor: "{colors.disabled-text}"
    cursor: not-allowed
  form-help-text:
    typography: "{typography.caption}"
    color: "{colors.on-surface-subtle}"
    marginTop: 4px
  form-error-text:
    typography: "{typography.caption}"
    color: "{colors.error}"
    marginTop: 4px
    fontWeight: 600
  tabs:
    borderBottom: "1px solid {colors.border-default}"
  tab-item:
    padding: "{spacing.3} {spacing.5}"
    typography: "{typography.button}"
    color: "{colors.on-surface-subtle}"
    borderBottom: "2px solid transparent"
  tab-item-active:
    color: "{colors.primary}"
    borderBottom: "2px solid {colors.primary}"
  breadcrumb:
    typography: "{typography.caption}"
    color: "{colors.on-surface-subtle}"
    separator: "/"
  breadcrumb-current:
    color: "{colors.on-surface}"
    fontWeight: 600
  pagination-item:
    width: 32px
    height: 32px
    rounded: "{rounded.md}"
    textColor: "{colors.on-surface-secondary}"
  pagination-item-active:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
---

# Nova Design System

## Overview

Nova is an open-source ERP for small F&B distributors — warehouse workers, salesmen on the road, accountants closing the month. The design system serves operators who use the same tools every day, in focused work mode, across desktop and mobile. The emotional tone is **authoritative, direct, and warm** — like an industry veteran who tells you what's happening without fluff. The system must never feel playful, never use ERP jargon in UI copy, and never hide critical data behind hover interactions. Every screen assumes the user has work to do and wants to get it done.

## Colors

The palette is built around a deep navy foundation (`#1a1a2e`) and a purple primary (`#5d3fd3`). Navy anchors the sidebar — always present, always calm. Purple signals what is actionable: buttons, links, active states, focus indicators. On light backgrounds, purple is bold and confident. On dark mode, it shifts to a lighter lavender (`#cabeff`) for readability.

Surfaces are clean and low-contrast: page body is a subtle off-white (`#f5f5f9`), cards are white (`#ffffff`), and borders stay light (`#e0e0e0`). The hierarchy goes body → surface → border → text, never fighting for attention. Semantic colors use soft background tints with bold text — a green badge on pale green, red on pale red — so they read at a glance without shouting.

Dark mode inverts the spectrum: body becomes deep indigo (`#0f0f1a`), surfaces are navy (`#1a1a2e`), purple becomes light lavender, and all text/background pairs maintain WCAG AA contrast.

**Enhancement — contrast audit.** The original `on-surface-subtle` (`#888888`) measured ~3.5:1 on white, below the 4.5:1 AA threshold for normal-weight text, even though it was used for real copy (page subtitles, empty-state messages). It's been darkened to `#767676` (~4.6:1) so it's safe for body-sized text. `on-surface-faint` (`#999999`) stays lighter but is now scoped strictly to decorative or large-scale uses — timestamps next to other text, disabled icons, hex captions in this guide — never as the only color for a sentence someone needs to read. Two new tokens round out interaction states that weren't previously defined: `disabled-bg` / `disabled-text` for non-interactive controls, and `focus-ring`, a dedicated color for the keyboard-focus outline (previously only inputs had a focus treatment; buttons, links, and table rows had none, which fails keyboard-navigation requirements for the warehouse and back-office users who rely on tab order).

## Typography

Nova uses a bilingual font stack — one typeface for Latin scripts, one for Arabic — selected for visual harmony, equivalent weight matching, and identical x-height ratios so that mixed-language UIs feel seamless.

| Script | Font | License | Weights |
|--------|------|---------|---------|
| Latin (English, etc.) | **Inter** | SIL OFL | 100–900 (variable) |
| Arabic (Arabic, Farsi, Urdu) | **Noto Sans Arabic** | SIL OFL | 100–900 (variable) |
| Code / Identifiers | **JetBrains Mono** | SIL OFL | 100–800 |

### Latin: Inter

Inter is the UI typeface for all Latin-based text — a clean, neutral neo-grotesque sans-serif with excellent legibility at small sizes. Its tall x-height and open apertures make it ideal for dense ERP data tables and forms.

### Arabic: Noto Sans Arabic

Noto Sans Arabic is Google's comprehensive Arabic typeface, designed to pair with Inter's neutral-modern aesthetic. It follows the Naskh style with simplified, legible shapes suitable for UI at small sizes. The weight axis (100–900) matches Inter's weight scale exactly, so a `font-weight: 600` button reads consistently across both scripts.

**Why Noto Sans Arabic over alternatives:**
- **Best weight parity with Inter** — identical 100–900 scale with matching visual density
- **Variable font** — single file covers all weights, reducing bundle size
- **Broad character coverage** — Arabic, Farsi, Urdu, Kurdish, and full Latin fallback
- **Active maintenance** — updated regularly by Google's font team

### Implementation

Font switching is driven by the `lang` attribute on `<html>`:

```css
/* Latin (default) */
body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }

/* Arabic */
html[lang="ar"] body {
  font-family: 'Noto Sans Arabic', 'Tahoma', sans-serif;
  line-height: 1.6; /* increased for Arabic ascenders/descenders */
}
```

Every typography token in the design system has a `fontFamily` (Latin) and `fontFamilyAr` (Arabic) counterpart. Mixing scripts within the same view (e.g., an English product name in an Arabic interface) falls back gracefully since both fonts cover Latin and Arabic respectively.

### Type Scale

The ERP context means most text is small (13px body, 11px table headers) so character spacing and weight differentiation do the work of hierarchy rather than size. Headings are bold but restrained (22px h1 is the largest in-app). Button labels are always 13px / 600 weight — never smaller or lighter. Table headers are 11px uppercase with subtle letter-spacing, visually distinct from data rows without needing background colors. Code and identifiers use JetBrains Mono at 12px for inline differentiation. The landing page uses a larger display size (40px / 800 weight) for the hero headline, but this never appears inside the application.

## Layout

The layout follows a consistent navigation + content pattern. Nova supports two interchangeable navigation modes — **sidebar** (default, persistent left rail) and **top bar** (Odoo-style module switcher + horizontal sub-nav) — see [Navigation Modes](#navigation-modes) below. Whichever is active, the content area itself doesn't change: pages use a page header at the top (title + subtitle + optional action button), then a single card containing a data table or detail view. There is no dashboard grid, masonry, or multi-column narrative — the reading order is always top-to-bottom, left-to-right.

The spacing scale is based on a 4px unit: margins and gaps use 4, 8, 12, 14 (form rows), 16, 20, 24, 32, 40, and 48px. The most common rhythm is 24px between sections (page header → card, card → next section) and 14px between form rows. At mobile widths (below 768px), cards collapse to edge-to-edge, form rows stack to single column, and page headers stack vertically. The grid system exists only as lightweight inline styles (`display: grid; grid-template-columns: 1fr 1fr; gap: 14px`) — there is no grid framework.

## Elevation & Depth

Elevation is deliberately quiet. Cards use a subtle border (`1px solid #e0e0e0`) plus a minimal drop shadow (`0 1px 3px rgba(0,0,0,0.05)`). Modals use a stronger shadow (`0 8px 32px rgba(0,0,0,0.2)`) to indicate they sit above the page surface. Hover states use a lighter background tint (`var(--bg-surface-hover)`) rather than elevation change — nothing jumps at the user. The landing page uses a slightly stronger shadow on its pricing card (`0 4px 24px rgba(0,0,0,0.08)`) for visual emphasis, but inside the app, elevation is understated. This philosophy communicates reliability: the system sits flat and doesn't surprise.

**Enhancement — stacking order.** Shadows describe depth, but nothing previously governed which layer wins when a dropdown, a sticky table header, a modal, and a toast are on screen together — a common state in a data-entry-heavy ERP (e.g., a select menu open inside a modal while a save-confirmation toast fires). A `zIndex` scale fixes this: `dropdown` (10) and `stickyHeader` (20) sit above normal page content; `overlay`/`modal` (100/101) sit above those; `toast` (200) always surfaces above modals so confirmations are never hidden; `tooltip` (300) is topmost since it's transient and small. Components should reference these tokens rather than ad-hoc `z-index` values.

## Shapes

Corner radius follows component role. Buttons and selects use 8px — rounded but still businesslike. Inputs and icon buttons use 6px, slightly tighter. Cards, modals, and the main data container use 12px, creating a soft frame for content. Badges and toggle switches use full rounding (9999px). The radius scale never goes below 4px (used only for skeleton placeholders). The system never uses sharp 0px corners on interactive elements — every clickable target has a visible anchor radius. 12px on cards signals a modern, approachable tool; 6–8px on inputs keeps them clearly editable without being cute.

## Components

**Buttons** follow a primary / outline / secondary / icon taxonomy. Primary buttons (`button-primary`) use the brand purple with white text, outline buttons have a 1px border with transparent background, secondary buttons sit on the surface-hover background, and icon buttons are 36×36px squares with no border. All interactive buttons have a minimum touch target of 44px height per WCAG guidelines. The `button-sm` and `button-xs` variants reduce padding but maintain minimum height. Icon buttons shift to `--color-primary` on hover as a feedback cue; the danger variant shifts to red.

**Inputs** are unified under a single `form-input` class: 13px text, 6px radius, subtle border, 8px padding. The `input-error` class swaps the border to `#dc2626` via a form-validation pattern. Checkboxes use `accent-color: #5d3fd3` for native browser consistency. Toggle switches appear only in settings screens and follow a standard pill pattern with purple active color. Selects use native `appearance: auto` rather than custom dropdowns — the platform default is adequate for ERP quantity.

**Cards** (`data-card`) wrap every table or list with a 12px rounded container, white background, and 1px border. Inside, `data-table` strips all card-level chrome and uses subtle row hover states. `detail-card` variants follow the same pattern for record detail views. `stat-card` renders centered stat values for dashboard-style displays.

**Modals** use a semi-transparent overlay (`rgba(0,0,0,0.4)`) with centered 580px container. The narrow variant (`modal-sm`) is 420px for confirmations. All modals follow header / body / footer anatomy. The confirm dialog (`ConfirmDialog.vue`) is a teleported overlay with a title, message, and two action buttons.

**Badges** are fully rounded pills with 11px bold text. They carry status meaning through color combinations: green (active/approved/completed), red (danger/cancelled/error), amber (warning/pending/draft), blue (info/in-progress), gray (inactive/disabled). Each combination has a soft tinted background and bold semantic text color.

**Skeletons** use 4px rounded animated placeholders for loading states. Three variants exist: `skeleton-table` (row pattern), `skeleton-card` (general content), and `skeleton-form` (form field simulation). They animate via CSS gradient shift with a custom dark-mode color pair.

**The sidebar** is a permanent vertical navigation, 240px expanded and 64px collapsed. It uses navy background (`#1a1a2e`) with muted text (`#ccc`) and purple active states (`#cabeff`). Navigation sections are separated by 11px uppercase group headers. Each nav item has a left-border active indicator.

### Navigation Modes: Sidebar vs. Top Bar

Nova's nav tree is wide — many modules, each with several subgroups. A single sidebar that lists everything works fine for a handful of modules, but as the tree grows it either scrolls forever or needs collapsible groups nested inside collapsible groups, which is where most ERP sidebars stop being navigable. The alternative, used by Odoo and similar systems, is to split navigation into two tiers: a top bar for switching **between** modules, and a horizontal sub-nav for moving **within** the current module. Nova now supports both as an interchangeable `navMode` (`sidebar` | `topbar`), sharing the same underlying route tree — only the chrome around it changes.

**Top bar anatomy** (56px, reuses `sidebar-bg` navy for brand continuity — this isn't a second color language, just the sidebar rotated 90°):
- **Module switcher** (far start-edge): a 40×40px trigger that opens a `module-switcher-panel` — a popover grid of `module-tile`s, one per top-level module, each with an icon and label. This replaces the sidebar's full module list; only the *current* module's sections show elsewhere.
- **Current module name**, next to the switcher, in `topbar-item` styling.
- **Module sub-nav**, directly under the top bar: a horizontal strip of that module's sections, using the same `tabs`/`tab-item` component already defined for record detail views — one component, two jobs. Active section gets the purple underline, same as any other tab.
- **Utility icons** (far end-edge): search, notifications, user menu — same `button-icon` component as everywhere else in the system.

**When to use which:**
- **Sidebar** suits a deployment scoped to a handful of modules (a single-warehouse customer using only Sales + Inventory), where seeing every section at a glance without an extra click is worth the vertical rail.
- **Top bar** suits the full Nova install — 17+ modules — where a persistent list of everything would either dominate the screen or force nested collapsing. It also reclaims horizontal width for wide data tables, which matters more here than in a typical SaaS app given how dense Nova's tables already are.
- Both read the identical route/permission tree, so switching modes is a display preference (per-tenant default, optionally per-user), never a data-modeling decision.

**RTL note:** the module switcher trigger stays at the *start* edge in both directions (left in LTR, right in RTL) — it's the equivalent of "home," not a directional control, so it doesn't need mirroring logic beyond the standard `dir="rtl"` flex-reverse. The sub-nav's tab order also reverses with `dir`, consistent with the RTL rules already defined for tabs.

**Mobile:** the top bar collapses the module name (icon only) and the sub-nav becomes horizontally scrollable rather than wrapping — the same treatment table headers get on narrow viewports. The sidebar's existing 64px collapsed-icon-rail behavior stays as-is for teams that keep sidebar mode on mobile.

### New components (enhancements)

**Disabled states** were previously undefined — every button and input in the system had normal, hover, and error variants, but no way to render "not applicable right now" (a Save button before required fields are filled, a locked line item on a posted invoice). `button-disabled` and `input-disabled` use a flat `disabled-bg` fill with `disabled-text`, no border emphasis, and `cursor: not-allowed`. They never use opacity tricks, which can wash out badge colors sitting inside a disabled row.

**Form help & error text** give inputs a place to explain themselves. `input-error` previously only recolored the border; there was no token for the message underneath it. `form-help-text` (muted, for guidance like "Format: DD/MM/YYYY") and `form-error-text` (red, bold, for "This field is required") sit 4px below the input, using the existing caption typography so they don't compete with the label above.

**Tabs** organize a single record's sub-views (a customer's Details / Orders / Ledger / Documents) without leaving the page — a pattern the current system needs for detail views but never formalized. Tabs sit on a bottom border, inactive tabs are muted, and the active tab gets a 2px primary-colored underline plus a color change — never color alone, so the active state survives color-blindness and grayscale printing.

**Breadcrumbs** give orientation in deep hierarchies (Warehouse → Pick Lists → PL-2044) that the sidebar alone can't express, since the sidebar shows section, not record depth. They're small caption-sized text with a `/` separator; the current page is bold and full-contrast, every ancestor is muted and clickable.

**Pagination** was missing despite `data-table` being the system's core content pattern — any product list, order list, or ledger beyond a page will eventually need it rather than rendering thousands of rows. Page items are small 32×32px squares, keeping to the same restrained, non-playful visual language as the rest of the system; the active page fills with primary purple.

### RTL & icon mirroring

Flipping `dir="rtl"` mirrors layout, but not every icon should mirror with it. **Do mirror:** back/forward chevrons, arrows indicating reading-order navigation (breadcrumb separators, pagination prev/next), and text-alignment icons. **Don't mirror:** play/pause icons, refresh/sync icons, checkmarks and status icons, brand logos, and numeric or currency figures — mirroring these either has no meaning or actively reverses their intent (a mirrored "refresh" arrow still means refresh; a mirrored play button looks like it points the wrong way for media, which Nova doesn't have, but the rule generalizes to any future icon work). When in doubt, mirror only icons whose meaning is inherently directional.

## Do's and Don'ts

**Do's:**
- Do use direct, action-oriented copy: "Order placed. Inventory updated. Warehouse has their pick list."
- Do show empty states that guide the user: "No picks waiting. Once a salesman places an order, it'll show up here."
- Do maintain 44px minimum touch targets on all buttons and interactive controls.
- Do use font-weight and letter-spacing for hierarchy before reaching for color or size.
- Do support light and dark mode as equals — every color token has a dark counterpart.
- Do right-to-left layout (RTL) for Arabic localization, applied at the `[dir="rtl"]` attribute level.
- Do give every interactive element a visible `focus-ring` outline for keyboard navigation — not just inputs.
- Do reserve `on-surface-faint` for decorative or large-scale use only; use `on-surface-subtle` or darker for any real sentence someone has to read.
- Do treat `navMode` (sidebar vs. top bar) as a display preference reading the same route tree — never fork navigation data per mode.

**Don'ts:**
- Don't use ERP jargon in UI copy. No "Error code: ERR-8472," no "streamlined onboarding experience."
- Don't hide critical data (stock levels, order status, pricing) behind hover or expand interactions.
- Don't add playful elements — Nova is a tool for daily work, not a consumer app.
- Don't use fully sharp (0px) corners on any interactive element.
- Don't add animation beyond 0.15–0.25s transitions — no bounce, no spring, no parallax.
- Don't introduce a grid framework or CSS framework — the existing layout patterns are sufficient.
- Don't mirror icons whose meaning isn't directional (refresh, play, checkmarks, logos) when flipping to RTL.
- Don't hide a "not applicable" control behind opacity alone — use the explicit `disabled-bg`/`disabled-text` pair so it stays readable and doesn't wash out adjacent color.

## Recommended next steps

These weren't built into the tokens above because they need a decision from you first, but are worth planning for:

- **Tenant theming layer.** If Nova is ever white-labeled per customer, define a narrow "brand override" surface — likely just `primary` / `primary-hover` / `primary-faded` — that a tenant config can safely override, while every neutral, semantic, and typography token stays locked. This prevents a customer's brand color from accidentally breaking contrast on error/success states.
- **Density modes.** Warehouse floor users scanning barcodes and accountants reconciling ledgers want different row density. A `data-table--compact` variant (tighter cell padding, e.g. `spacing.2` instead of `spacing.3`) toggled per-user would serve both without a second design system.
- **Print stylesheet.** An ERP generates invoices, pick lists, and statements that get printed. A `@media print` layer (hide sidebar/nav chrome, force light theme, add letterhead margins) is worth scoping as its own small spec before it's needed ad hoc inside a feature branch.
- **Chart/report palette.** Financial and inventory reporting will eventually need a categorical data-visualization palette (5–8 hues) distinct from the semantic colors, so a bar chart doesn't accidentally borrow the "error" red for a neutral category.
