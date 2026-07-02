---
name: Nova Enterprise
colors:
  surface: '#f9f9ff'
  surface-dim: '#d3daef'
  surface-bright: '#f9f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f1f3ff'
  surface-container: '#e9edff'
  surface-container-high: '#e1e8fd'
  surface-container-highest: '#dce2f7'
  on-surface: '#141b2b'
  on-surface-variant: '#484554'
  inverse-surface: '#293040'
  inverse-on-surface: '#edf0ff'
  outline: '#797586'
  outline-variant: '#c9c4d7'
  surface-tint: '#6042d6'
  primary: '#451ebb'
  on-primary: '#ffffff'
  primary-container: '#5d3fd3'
  on-primary-container: '#d8ceff'
  inverse-primary: '#cabeff'
  secondary: '#006a6a'
  on-secondary: '#ffffff'
  secondary-container: '#90efef'
  on-secondary-container: '#006e6e'
  tertiary: '#3d4551'
  on-tertiary: '#ffffff'
  tertiary-container: '#555c69'
  on-tertiary-container: '#ced4e4'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#e6deff'
  primary-fixed-dim: '#cabeff'
  on-primary-fixed: '#1c0062'
  on-primary-fixed-variant: '#4723be'
  secondary-fixed: '#93f2f2'
  secondary-fixed-dim: '#76d6d5'
  on-secondary-fixed: '#002020'
  on-secondary-fixed-variant: '#004f4f'
  tertiary-fixed: '#dce2f3'
  tertiary-fixed-dim: '#c0c7d6'
  on-tertiary-fixed: '#151c27'
  on-tertiary-fixed-variant: '#404754'
  background: '#f9f9ff'
  on-background: '#141b2b'
  surface-variant: '#dce2f7'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  title-md:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.05em
  data-mono:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '450'
    lineHeight: 18px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  gutter: 16px
  margin-mobile: 16px
  margin-desktop: 32px
  max-width: 1440px
---

## Brand & Style

This design system is engineered for high-density enterprise environments where efficiency and clarity are paramount. The brand personality is **authoritative, analytical, and frictionless**. It draws from **Corporate Modernism**, prioritizing a modular architecture that feels both solid and adaptable.

The aesthetic avoids unnecessary decoration, focusing instead on structural integrity and data legibility. It utilizes a refined "Systematic Layering" approach—using subtle tonal shifts rather than heavy shadows to define hierarchy. This ensures the UI remains performant and visually quiet even when displaying complex datasets or multi-step workflows.

The target audience consists of power users in finance, logistics, and management who require a tool that responds predictably and scales effortlessly across global markets.

## Colors

The palette is anchored by a **Deep Iris Purple** (#5D3FD3) primary color, chosen for its sophisticated and modern professional feel. This is complemented by a **Strategic Teal** (#008080) for secondary actions and success states, providing a clear visual distinction from primary workflows.

The neutral scale is expansive, using cool-toned grays to manage information density. 
- **Primary:** Core actions, active states, and brand presence.
- **Secondary:** Supporting data points, analytics highlights, and secondary navigation.
- **Neutral:** Typography, borders, and structural surfaces.
- **Semantic:** Standardized red for errors (#DC2626), amber for warnings (#D97706), and teal for success.

The default mode is `light`, providing a high-contrast environment for prolonged daylight work, though the token structure is built to support a "Dim" or "Dark" theme by swapping the neutral ramp.

## Typography

Typography is the backbone of this design system's utility. We use **Inter** for all Latin-based characters due to its exceptional legibility in UI and its tall x-height, which aids readability in dense tables. For Arabic locales, the system switches to **IBM Plex Sans Arabic**, ensuring a harmonious weight match and professional tone.

**Key Rules:**
- **Numerical Data:** Use `data-mono` (JetBrains Mono) for financial columns and ID tags to ensure tabular alignment.
- **Hierarchy:** Use font weight (Medium/Semi-Bold) rather than size to differentiate headers in dense forms.
- **Bi-directional Support:** Line heights are slightly increased for Arabic scripts to accommodate larger ascenders and descenders without clipping.

## Layout & Spacing

This design system utilizes a **4px baseline grid** for internal component spacing and a **12-column fluid grid** for page layouts. 

- **Desktop:** 12 columns, 16px gutters, 32px side margins.
- **Tablet:** 8 columns, 16px gutters, 24px side margins.
- **Mobile:** 4 columns, 12px gutters, 16px side margins.

For ERP dashboards, use "Content-First Scaling." The sidebar is fixed at 240px (collapsible to 64px), while the main content area expands to fill the viewport. High-density views (like Data Tables) reduce internal cell padding to `sm` (8px), while marketing-oriented pages or empty states use `xl` (32px) padding to create breathing room.

## Elevation & Depth

To maintain a clean, "Odoo-inspired" aesthetic, depth is communicated through **Tonal Layering** and **Subtle Stroke** rather than heavy drop shadows.

- **Level 0 (Base):** Background (#F9FAFB).
- **Level 1 (Card/Surface):** White (#FFFFFF) with a 1px border (#E5E7EB). No shadow.
- **Level 2 (Popovers/Dropdowns):** White with a soft, 12% opacity neutral shadow and a 1px border.
- **Level 3 (Modals):** High-contrast shadow (20% opacity) with a background backdrop blur (4px) to focus user attention.

Interactive elements use a "Press Effect": buttons translate 1px down on click, and hover states involve a slight darkening of the surface color rather than a change in elevation.

## Shapes

The shape language is **Soft (0.25rem / 4px)**. This choice strikes a balance between the rigid "sharp" corners of legacy enterprise software and the overly "bubbly" feel of consumer apps. 

- **Small Components:** Checkboxes, tags, and input fields use `rounded` (4px).
- **Medium Components:** Buttons, cards, and dropdown menus use `rounded-lg` (8px).
- **Large Components:** Modals and large dashboard containers use `rounded-xl` (12px).

In RTL layouts, all asymmetrical shapes (like icons with directionality) must be mirrored, while circular avatars and status dots remain static.

## Components

### Buttons
- **Primary:** Iris Purple background, White text. No border.
- **Secondary:** White background, Iris Purple border (1px), Iris Purple text.
- **Ghost:** Transparent background, Neutral-600 text. Used for "Cancel" or low-priority actions.

### Data Tables
- **Header:** Light gray background (#F3F4F6), 12px Semi-Bold Label typography.
- **Row:** 48px minimum height. On hover, apply a 2% Iris Purple tint to the entire row.
- **Cell:** Horizontal borders only. Use `data-mono` for numeric columns.

### Input Fields
- **Default State:** 1px Neutral-300 border.
- **Focus State:** 2px Iris Purple border with a soft 2px purple outer glow (30% opacity).
- **Label:** Always visible above the input, never floating inside, to maintain accessibility.

### Dashboards & Cards
- Use "Header-Action" cards: a clear title on the left and a contextual action (like a "Filter" or "Export" icon-button) on the right.
- Ensure all cards have a consistent padding of 24px (lg).

### RTL Adjustments
- Icons representing progress (arrows, loading bars) must flip direction.
- Form labels must align to the right.
- The primary navigation sidebar shifts from the left to the right side of the screen.