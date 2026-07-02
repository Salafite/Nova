# Vision — Nova

> Captured by the Product Planner skill. This file is the source of truth for
> generating product-vision.md, prd.md, and product-roadmap.md. Edit it directly
> and re-run the Product Planner to regenerate downstream documents.

**Created:** 2026-07-02
**Updated:** 2026-07-02

## Founder

- **Name:** Mohamed Adel
- **Expertise:** Industry solution architect, SaaS/ERP consultancy with Odoo partnership, M3/integration SME, AI orchestration for Infor
- **Background:** Built Makka's first C# ERP system 10 years ago — it's still running on an isolated server, and they've asked multiple times for a backup and data purge because they've outgrown it. Runs a 2-person consultancy doing ERP consulting, software development, and digital transformation.

## Purpose

- **Who you help:** Small F&B distributors (grains, oil, spices, perishables) doing 5–50M/month, starting with Makka as the first customer — a specific 20M/month business with 8 salesmen, 2 accountants, and 2 warehouse workers.
- **Problem you solve:** The old system can't scale — salesmen can't see real-time inventory so they over-promise, warehouse gets orders that don't match picks, accountants chase payment reconciliation mismatches. Phantom products clutter the catalog. No clean customer balance tracking across installment, check, and cash payments. POS is disconnected from core operations.
- **Desired transformation:** Orders flow end-to-end in real time. Salesmen see live inventory, warehouse gets correct picks instantly, accountants see receivables and customer balances created automatically. Legacy clutter cleaned up. All payment methods tracked in one place.
- **Why you:** Built Makka's first system 10 years ago, it's still running, and they came back to you because they've outgrown it. No one else has that decade of context, trust, and institutional knowledge.

## Product

- **Name:** Nova
- **One-liner:** A modular ERP for small F&B distributors that starts with an end-to-end order → inventory → warehouse → accounting flow.
- **How it works:** Salesman places an order — inventory is reserved in real time — warehouse sees the pick list instantly — accountant sees the receivable and customer balance updated. POS and multi-payment methods (installment, check, cash) connected to the same system.
- **Key capabilities:**
  - Real-time inventory tracking
  - Order management with live stock reservation
  - Automated pick list generation
  - Accounts receivable with multi-payment tracking (installment, check, cash)
  - Product catalog management (phantom product cleanup)
  - POS integration
  - Basic supplier management
- **Platform:** web
- **Market differentiation:** Vertical-first (F&B) with horizontal expansion — not a generic ERP. Open-source community edition + affordable $5/user/month pricing. Decade of institutional context from building the customer's legacy system.
- **Magic moment:** Salesman places an order → inventory updates in real time → warehouse sees the correct pick list → accountant sees the receivable created. The three-person cascade broken in a single flow.

## Audience

- **Primary user:** Makka — a grains, food oil, and spices distributor doing ~20M/month. 8 salesmen who need live inventory visibility, 2 warehouse workers who need accurate picks, 2 accountants who need clean receivables and customer balance tracking. Their legacy C# system (built by the founder) is running on an isolated server and they've asked multiple times for a replacement.
- **Secondary users:**
  - Other F&B distributors (5–50M/month) in the founder's Odoo partner channel
  - Construction industry businesses (long-term expansion)
- **Current alternatives:** 10-year-old C# system (built by the founder) + spreadsheets + manual coordination (salesmen calling warehouse, accountants chasing paper) + disconnected POS
- **Frustrations:** Old system can't handle scale (phantom products, no real-time inventory), disconnected POS creates double entry, no unified multi-payment tracking, daily manual handoffs cause errors across all 3 roles

## Business

- **Revenue model:** subscription
- **90-day goal:** Makka live on Nova
- **6-month vision:** Makka live + Nova open-source community growing with contributors (Odoo-like community play)
- **Constraints:** 2-person team (~4 hours/day each currently), scalable to 5 people. Consultancy work alongside the build. Hybrid deployment (on-prem or cloud) adds DevOps complexity.
- **Go-to-market:** Direct to F&B distributors in existing Odoo partner channel (Makka as case study) + open-source community / build in public (GitHub release, community edition) + long-term expansion to construction industry

## Brand Voice

- **Personality:** The industry veteran — knows the F&B distribution world inside out. Authoritative, trustworthy, speaks the user's language.
- **Tone of voice:** Warm but professional. Conversational but focused. Example: "Orders processed. The warehouse team has their picks. Want a summary sent to accounting?"

> Visual identity (mood, anti-patterns, design tokens) is deliberately not
> captured here — it lives in docs/design.md, generated by the Design System
> skill from image references.

## Tech Stack

- **App type:** web
- **Frontend:** Nuxt 3 — Vue framework with batteries-included conventions, SSR, module ecosystem
- **Backend:** FastAPI — modern Python async framework, type-hint validation, auto OpenAPI docs
- **Database:** PostgreSQL — the right choice for ERP with complex relational data
- **Auth:** Auth0 — enterprise-ready, works with Python backend, social login and MFA out of the box
- **Payments:** Stripe — flexible, handles subscription billing for $5/user/month model
- **Analytics:** PostHog — free tier covers early volume, session replay and feature flags bundled
- **Email:** Resend — transactional email for notifications, receipts, and account management
- **Error tracking:** Sentry — catch crashes in production before users report them
- **Deployment:** Hybrid (on-prem via Podman containers or cloud) — app configured via environment variables

## Tooling

- **Coding agent:** Other: Claude Code, opencode, local LLM (Qwen 3 35B A3B), Ornith 1.0
