# Product Vision — Nova

## 1. Vision & Mission

### Vision Statement
A world where every F&B distributor — from the small grocery to the regional wholesaler — runs operations on open, affordable software that adapts to their business instead of forcing them to adapt to it.

### Mission Statement
Nova gives small F&B distributors a modern, open-source ERP that replaces decade-old legacy systems with real-time inventory, automated order-to-cash flows, and a single source of truth across sales, warehouse, and accounting.

### Founder's Why
Mohamed Adel built Makka's first ERP system 10 years ago as a 25-table C# application. It solved their problems at small scale, and they've run their business on it ever since — it's still running on an isolated server. But Makka has grown to 20M/month with 12 staff, and the old system is cracking. Salesmen can't see real inventory, warehouse gets wrong picks, accountants chase payment entries. They've asked Mohamed multiple times for a backup and data purge just to keep the system limping along.

Mohamed didn't just build that system — he's lived in the ERP world for a decade. M3 SME, Odoo partnership, AI orchestration at enterprise scale for Infor. He knows what a well-built ERP looks like and what shortcuts break. Nova isn't a first attempt at an ERP — it's the consolidation of ten years of seeing what works, what doesn't, and what small distributors actually need.

### Core Values

**Ship a working flow, then expand.** Nova ships the core order-to-cash flow first — not all modules at once. Every release must be usable by a real business. Perfection is deferred; value is not.

**Open source by default.** The community edition is free. Businesses pay for hosting, support, and additional modules at $5/user/month. This mirrors the Odoo model that proved open-source ERP can be a real business.

**The operator's language, not consultant-speak.** Every screen, error message, and workflow speaks the language of a warehouse worker or salesperson at an F&B distributor. No ERP jargon, no dashboard for the sake of dashboard.

**Ship on-prem and cloud from day one.** Not every F&B distributor trusts the cloud. Nova runs in Podman containers on their server or in your cloud. The architecture never forces a deployment model on the user.

### Strategic Pillars

**Vertical depth over horizontal breadth.** Nova wins by knowing F&B distribution better than generic ERPs. The first version is built for Makka's workflow; expansion is driven by adjacent distributors, not by adding random modules.

**Real-time as the default, not the upgrade.** Inventory, orders, picks, receivables — they update in real time across all roles. No refresh buttons, no "sync overnight."

**Legacy migration as a feature, not a project.** Nova is built by the person who wrote the old system. Migration tooling is part of the product, not an afterthought.

### Success Looks Like

Twelve months from now, Makka has been running Nova in production for 9 months. Salesmen open Nova on a tablet or phone, check live inventory, place an order, and the warehouse receives it instantly — the same flow that used to take three phone calls and generate two errors. Accountants reconcile payments (installment, check, cash) from a single customer view instead of chasing through three different systems. The open-source community has 20+ contributors, the GitHub repo shows steady activity, and 5 other F&B distributors are paying $5/user/month. Mohamed's team has grown from 2 to 5. The construction industry pilot is being discussed.

## 2. User Research

### Primary Persona

**Hassan** — 41, operations manager at a F&B distributor doing ~20M/month in grains, oils, and spices. He oversees 8 salesmen, 2 warehouse workers, and 2 accountants. He's been in the distribution business for 18 years and started using computers when the owner bought the "new C# system" 10 years ago.

Hassan's daily reality: he starts every morning with the overnight orders report from the old system — except the report often shows phantom inventory from products that were discontinued years ago. Salesmen call him asking "is this in stock?" because they don't trust the system. Warehouse workers come to his desk with pick lists that don't match what the salesman promised. Accountants bring payment reconciliation issues to him at least twice a week.

Hassan is not a power user of technology — he uses what works and complains loudly about what doesn't. He values reliability above all else. A system crash during the month-end close is his nightmare. He wants something his team will actually use, not another tool they'll ignore.

### Secondary Personas

**Khalid, salesman** — 29, one of Makka's 8 salesmen. He spends his day on the phone with customers, visiting stores, and checking stock. He currently calls the warehouse to ask about availability, writes orders on paper, and hopes they're correct. He wants to check inventory from his phone and place orders without calling anyone.

**Yara, accountant** — 35, one of Makka's 2 accountants. She manages receivables across cash, checks, and installment payments. Her current workflow involves cross-referencing three sources: the old system for orders, handwritten receipts from warehouse, and a separate POS system. She spends 3–5 hours per week just reconciling the three sources against each other.

### Jobs To Be Done

**Functional jobs:**
- Place an order and know within seconds whether inventory is available
- Receive a pick list that reflects the actual order, not a phone-call version
- See every customer's balance across all payment methods in one screen
- Close the accounting period without chasing discrepancies

**Emotional jobs:**
- Feel confident that the system reflects reality — no phantom stock, no surprise shortages
- Stop feeling embarrassed when customers ask "is it in stock?" and the answer is "I'll call you back"
- Sleep well during month-end close knowing the numbers are right

**Social jobs:**
- Look competent to the business owner when reporting weekly numbers
- Be seen as running a modern operation, not a pen-and-paper shop
- Justify the investment to the owner with clear results

### Pain Points

| Pain | Frequency | Current Workaround | Severity |
|---|---|---|---|
| Salesmen can't see real inventory | Daily (every order) | Call warehouse directly | High — lost sales, overselling |
| Warehouse picks don't match orders | Daily | Correct on the fly, re-pick, apologize | High — wasted labor, delays |
| Phantom products in catalog | Weekly (new orders) | Manual cleanup, flag to ops manager | Medium — confusion, errors |
| Payment reconciliation across 3 methods | Weekly (2-3 hours) | Cross-reference 3 sources manually | High — time sink, errors |
| POS disconnected from ERP | Daily | Double entry, manual sync | High — data inconsistency |
| Month-end close takes 3-5 extra days | Monthly | Chase discrepancies, manual adjustments | High — delays reporting to owner |

### Current Alternatives & Competitive Landscape

**The legacy C# system (built by the founder, 10 years old).** What it does well: the team knows it, it works reliably at small scale, all their data lives there. Where it falls short: phantom products, no real-time visibility, no mobile access, disconnected POS, no multi-payment tracking. Switching cost: high — years of data, embedded workflows, learned behavior.

**Spreadsheets and phone calls.** What they do well: flexible, everyone knows how to use them, zero cost. Where they fall short: no real-time sharing, error-prone, no audit trail, impossible to scale. Switching cost: low — spreadsheets are a symptom of the system failing, not a deliberate choice.

**Odoo.** What it does well: mature open-source ERP, huge module ecosystem, strong community. Where it falls short: overwhelming for small distributors, requires significant customization for F&B-specific workflows (lot tracking, perishable inventory, multi-payment), expensive at scale for a business of this size. Switching cost: medium — Odoo partners exist but the implementation cost is high.

**ERPNext.** What it does well: open-source, modern UI, simpler than Odoo. Where it falls short: less F&B-specific functionality, smaller community than Odoo, less ecosystem of partners. Switching cost: medium.

**The "do nothing" alternative.** Makka could keep running the old system with manual workarounds. They've been doing it for years. But the repeated requests for "backup and data purge" show this isn't sustainable — the system is degrading, and every month without migration adds risk.

### Key Assumptions to Validate

1. **F&B distributors will pay $5/user/month for an open-core ERP.** If the community edition is free, will enough businesses convert to paid? Test: gauge interest from 5 F&B distributors in the Odoo channel before building.
2. **Migration from a 10-year-old C# system is feasible without data loss.** The old system has a decade of accumulated data, phantom products, and schema drift. Test: run a full data audit of Makka's current system to understand the migration scope.
3. **The MVP order-to-cash flow alone justifies switching.** If Nova ships only order → inventory → warehouse → accounting with no POS or full accounting, is that enough for Makka to cut over? Test: offer Makka a concierge version of just the flow before building software.
4. **An open-source ERP community will form around Nova.** Odoo and ERPNext have years of head start. Is there room for another? Test: publish the MVP on GitHub and measure organic interest before investing in community infrastructure.
5. **Hybrid on-prem/cloud deployment is worth the engineering cost.** Building for both adds complexity. Is the on-prem audience large enough to justify it? Test: ask 10 F&B distributors whether cloud-only would be a dealbreaker.

### User Journey Map

**Awareness:** Hassan hears about Nova from his Odoo partner (Mohamed's consultancy). The pitch: "remember the system I built you 10 years ago? I'm building its replacement — open source, modern, built for your scale."

**Consideration:** Hassan asks for a demo. Mohamed shows him the real-time order flow: a salesman places an order on a phone, inventory updates instantly, warehouse sees the pick, accountant sees the receivable. Hassan's reaction: "Can I see it with our actual data?"

**First use:** Mohamed runs a concierge version for 2 weeks — he manually processes Makka's orders through a spreadsheet workflow that mimics the Nova flow. Hassan's team sees the difference immediately: fewer calls, fewer errors, faster close.

**Magic moment:** Khalid (salesman) is on the phone with a customer, checks live inventory on his phone, says "yes, 50 bags in stock" without calling the warehouse. He places the order. Warehouse receives it automatically. Khalid tells Hassan: "This actually works."

**Habit formation:** Within 3 weeks, Khalid won't place an order outside Nova. Warehouse won't pick without a Nova pick list. Accountants check the receivables screen at the start of every day instead of reconciling three sources.

**Advocacy:** Hassan mentions Nova to the owner of a similar F&B distributor at a trade association meeting. "We switched. It actually solved the inventory problem. My team uses it."

## 3. Product Strategy

### Product Principles

1. **Real-time is the only mode.** No batch updates, no nightly syncs, no refresh buttons. When inventory changes, every role sees it immediately.
2. **The smallest unit of value is one end-to-end transaction.** Partial features don't ship. A flow is done when a salesman can place an order and the accountant can see the receivable.
3. **Migration is part of the onboarding, not a separate project.** Nova comes with tooling to import data from the legacy C# system, clean phantom products, and reconcile payment histories.
4. **On-prem and cloud are equal citizens.** No cloud-first features that break when run locally. Every feature works in a Podman container with environment variable configuration.
5. **Open core, not open source charity.** The community edition is genuinely useful for a single-user business. The paid tier ($5/user/month) adds multi-user, advanced reporting, and support. The model sustains development.

### Market Differentiation

Generic ERPs like Odoo and ERPNext serve a wide market but require heavy customization for F&B-specific workflows — lot tracking, perishable inventory, multi-payment reconciliation (installment, check, cash), and the sales → warehouse → accounting cascade that defines distribution businesses. Nova is vertical-first: built for one industry's workflow, then expanded horizontally.

The real differentiator isn't a feature list — it's that the founder built Makka's current system. No competitor can offer a migration path from a 10-year-old C# system that they themselves wrote. Nova doesn't just replace the system; it replaces the decade of accumulated knowledge about what that system does, where its data lives, and what the team is used to.

The open-core model ($5/user/month for businesses, free for community) undercuts Odoo's per-module pricing and ERPNext's per-user pricing at small scale, making it affordable for the exact businesses that Odoo and ERPNext are too expensive for.

### Magic Moment Design

The magic moment is a single transaction flowing end-to-end: **a salesman places an order → inventory is reserved in real time → the warehouse receives a correct pick list → the accountant sees the receivable created.**

For this moment to happen reliably, three things must be true:

1. **Inventory accuracy** — the system must reflect what's actually in the warehouse. This means starting with a clean inventory audit (no phantom products) and real-time updates on every transaction.
2. **Real-time sync across roles** — when a salesman places an order, the warehouse and accountant must see it within seconds, not overnight. This requires the backend to push updates, not wait for polls.
3. **Each role sees their relevant view** — salesmen see products and availability; warehouse sees pick lists and locations; accountants see receivables and customer balances. No role sees the full system unless they need to.

The shortest path from sign-up to magic moment: upload inventory → define products → create a user for each role (salesman, warehouse, accountant) → place a test order → watch it flow end to end. A first-time user should experience the magic moment within their first 10 minutes.

### MVP Definition

**In scope for v1 (4–8 week build):**

1. **User authentication and role management** — Custom JWT login with three roles: Salesman, Warehouse, Accountant. Admin role for setup.
2. **Product catalog** — CRUD for products, categories, units of measure. Phantom product detection (flag products with no transactions in 12+ months).
3. **Real-time inventory tracking** — Stock levels per product, movement history, low-stock alerts. Updates propagate to all users instantly.
4. **Order management** — Salesman creates order, picks products, sets quantities. System checks and reserves inventory in real time. Order status tracking (draft → confirmed → picked → delivered → invoiced).
5. **Pick list generation** — Warehouse sees confirmed orders as pick lists. Items grouped by warehouse location. Pick confirmation with partial/all/backorder options.
6. **Accounts receivable entry** — On order confirmation, receivable is created. Basic payment tracking: installment, check, cash. Customer balance view across all methods.
7. **Supplier management** — Supplier profiles, contact info, linked products.
8. **Migration tool** — Import legacy data from Makka's C# system (products, customers, inventory, open orders).
9. **Admin panel** — User management, role assignment, system configuration.

### Explicitly Out of Scope

| Feature | Why Excluded | When to Reconsider |
|---|---|---|
| **Full accounting (GL, P&L, balance sheet)** | Out of scope for MVP — accounts receivable is enough to prove the flow. Requires separate financial accounting expertise. | After MVP, when customers ask for it |
| **POS module** | Disconnected POS is a pain point but solving the inventory cascade is the bigger win. Can be added as a module later. | After MVP, as a paid add-on module |
| **Budgeting and forecasting** | Not needed until the business has enough transaction history in Nova. | 6+ months post-launch |
| **Multi-warehouse** | Makka has one warehouse. Supporting multiple warehouses adds complexity without a customer. | When the second customer with multiple warehouses signs up |
| **Mobile apps** | Progressive web app (PWA) is sufficient for MVP. Native mobile apps can follow. | Post-MVP, based on user demand |
| **AI/automation features** | Tempting but doesn't test the core assumption. The AI orchestration expertise is a future differentiator. | After product-market fit is established |
| **Construction industry support** | Explicitly a future expansion. Nova is F&B-first. | 12+ month roadmap |
| **Open-source community infrastructure** | Repo can be public, but community infrastructure (docs site, forum, contributor guidelines) is deferred. | After MVP, when external interest emerges |

### Feature Priority (MoSCoW)

**Must Have (P0)**
- User auth and role management
- Product catalog with phantom detection
- Real-time inventory
- Order management with stock reservation
- Pick list generation
- Accounts receivable entry (basic)

**Should Have (P1)**
- Supplier management
- Migration tool for legacy C# system
- Customer balance view with multi-payment tracking

**Could Have (P2)**
- Low-stock alerts
- Order history and reporting
- PWA mobile-friendly interface

**Won't Have (this time)**
- Full accounting (GL, P&L, balance sheet)
- POS module
- Budgeting and forecasting
- Multi-warehouse
- Native mobile apps
- AI/automation features
- Construction industry support
- Open-source community infrastructure

### Core User Flows

**Flow 1: Salesman places an order**
Trigger → Khalid (salesman) receives a customer order over the phone
1. Khalid opens Nova on his phone or desktop
2. He searches the product catalog by name or category
3. He sees real-time stock levels for each product
4. He selects products, enters quantities, and confirms the order
5. System reserves inventory and updates stock in real time
6. Order status changes to "confirmed"
7. Success criteria: Khalid never has to call the warehouse to check stock. The customer gets an accurate delivery promise.

**Flow 2: Warehouse processes a pick list**
Trigger → A confirmed order appears in the warehouse dashboard
1. Warehouse worker opens Nova, sees "new picks" counter
2. Opens the pick list — items are grouped by warehouse location
3. Picks items, confirms each line (partial/all/backorder)
4. Order status changes to "picked"
5. Success criteria: The worker picks exactly what was ordered. No guessing, no phone calls to the salesman.

**Flow 3: Accountant sees the receivable**
Trigger → Order status changes to "delivered"
1. Accountant opens the receivables dashboard
2. Sees a new receivable entry with customer name, amount, payment method
3. Customer balance updates automatically
4. Accountant can see all payments (installment, check, cash) for that customer in one view
5. Success criteria: Accountant reconciles payments in one screen instead of cross-referencing three sources.

### Success Metrics

**Primary metric:** Time from order placement to receivable creation across the end-to-end flow. Target: < 30 seconds (down from hours/days of manual handoffs).

**Secondary metrics:**
- Orders placed without warehouse phone call check: > 90% within 30 days
- Pick list accuracy (picked items match ordered items): > 99%
- Payment reconciliation time per week: < 1 hour (down from 3-5 hours)
- Daily active users (DAU) per customer business: > 80% of staff

**Leading indicators:**
- Makka's salesmen use Nova for > 50% of orders within 2 weeks
- Warehouse stops accepting pick lists outside Nova within 2 weeks
- Accountants check the receivables dashboard daily

### Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Makka can't migrate data cleanly | Medium | Critical — stalls the only customer | Build migration tool early, test with real data before full build |
| $5/user/month is too low to sustain | Medium | High — unsustainable business model | Validate pricing with 5 F&B distributors before launch |
| Open-source community doesn't materialize | High | Medium — Nova works as a paid product | Don't depend on community for MVP; treat it as a bonus |
| Hybrid deployment makes development slow | Medium | High — slows iteration | Nail the cloud path first, add on-prem via Podman containerization as a parallel track |
| 2-person team can't ship MVP in 8 weeks | Medium | High — scope creep | Ruthless about out-of-scope list. No exceptions for "small additions." |

## 4. Brand Strategy

### Positioning Statement

For small F&B distributors who have outgrown their legacy systems, Nova is the open-source ERP that delivers real-time order-to-cash flow across sales, warehouse, and accounting. Unlike generic ERPs like Odoo or ERPNext, Nova is built from a decade of direct experience running an F&B distribution business on a custom system — with migration tooling written by the person who built the old one.

### Brand Personality

Nova is the industry veteran who has seen it all. Not flashy, not trying to impress you with buzzwords. When Nova speaks, it's with the authority of someone who has spent 18 years in the F&B distribution warehouse. It's the operations manager who remembers every workaround the team tried and knows why they didn't work.

- **Authoritative** — not arrogant. Nova tells you what's happening because it knows.
- **Trustworthy** — no phantom data, no surprises. What the screen shows is what's real.
- **Direct** — "50 bags of sunflower oil remaining. 3 shipments due tomorrow." Not fluff.
- **Warm** — it knows the team, their workflows, and why they do things a certain way. Doesn't judge the old system — just offers a better one.

### Voice & Tone Guide

| Context | Do | Don't |
|---|---|---|
| **Onboarding** | "Welcome back. We found 1,247 products in your old system. Let's clean out anything that hasn't been ordered in 12+ months." | "Let's get started with our streamlined onboarding experience!" |
| **Error state** | "Couldn't save the order. Your connection dropped. It's saved as a draft — resume when you're back online." | "An error occurred. Please try again or contact support. Error code: ERR-8472." |
| **Success message** | "Order placed. Inventory updated. The warehouse team has their pick list." | "Congratulations! Your order has been successfully processed and submitted." |
| **Empty state** | "No picks waiting. Once a salesman places an order, it'll show up here automatically." | "There are currently no items in this view. Create a new order to get started." |
| **Marketing copy** | "Built for F&B distributors who've outgrown their spreadsheets and legacy systems. Real-time inventory. Correct picks. Clean receivables." | "Next-generation AI-powered ERP solution for agile distribution enterprises." |
| **Low stock alert** | "Sunflower oil — 20 bags left. Your top supplier has 200 ready. Order now?" | "Inventory threshold breach detected for item #4582-FO. Immediate replenishment recommended." |

### Messaging Framework

**Tagline:** The ERP that knows your inventory, your customers, and your business.

**Homepage headline:** Nova gives your sales, warehouse, and accounting team the same real-time picture of your business.

**Value propositions:**
1. **Real-time inventory** — your salesmen see what's in stock before they promise it. No more calling the warehouse.
2. **Orders flow end to end** — a single order goes from salesman to warehouse to accounting without a single phone call.
3. **Built for F&B distributors** — not a generic ERP customized, but a system designed for how you actually work.

**Feature descriptions:**
- "Inventory tracking that updates the moment a pick is confirmed. No batch sync, no overnight updates."
- "Pick lists grouped by warehouse location. Warehouse workers pick faster, with fewer errors."
- "Customer balances across installment, check, and cash in one view. Accountants close faster."

**Objection handlers:**
- "We can't migrate from our old system" → "We built your old system. Migration is literally a feature."
- "We don't trust the cloud" → "Nova runs in containers. Your server or ours."
- "ERPs are too expensive for our size" → "$5/user/month. Free community edition. You pay when it's delivering value."

### Elevator Pitches

**5-second:** Nova gives F&B distributors real-time inventory and automated order-to-cash flows at $5/user/month.

**30-second:** Small F&B distributors hit a ceiling with their legacy systems and spreadsheets — salesmen can't see inventory, warehouse picks wrong items, accountants chase payment mismatches. Nova connects the three roles in real time. Orders flow end to end. Built open-source, deploy on-prem or cloud, starting at $5/user/month.

**2-minute:** F&B distributors like Makka — doing 20M/month in grains, oils, and spices — run their business on a 10-year-old C# system that can't keep up. Salesmen call the warehouse to check stock because they don't trust the system. Warehouse workers pick what they think the customer ordered. Accountants reconcile three different sources to close the books. Every month, it gets worse.

Nova replaces that with a single real-time system. A salesman places an order — inventory is reserved instantly. The warehouse sees the correct pick list. The accountant sees the receivable. All three roles see the same reality, in real time, without manual handoffs.

I built Makka's current system 10 years ago. They came back to me because they know I understand their business. Nova is what I'd build if I started over — modern, open-source, affordable, and built for how F&B distribution actually works.

The business model is simple: the community edition is free for anyone to use. Businesses pay $5/user/month for multi-user, advanced features, and support. Implementation services generate consulting revenue. Over time, modules expand into adjacent industries.

### Competitive Differentiation Narrative

Odoo and ERPNext are powerful platforms, but they're built for the broadest possible market. A small F&B distributor implementing Odoo spends weeks configuring modules, writing custom workflows for lot tracking and perishable inventory, and training a team that doesn't think in terms of "sales orders" and "delivery orders" — they think in terms of customer calls, warehouse picks, and monthly close. ERPNext is simpler but still generic, and its community and partner ecosystem are smaller.

Nova starts in the opposite direction: built for one industry's workflow, then expanded. The migration path is the killer advantage — Mohamed wrote Makka's legacy C# system, knows every table, every workaround, every piece of accumulated data debt. No competitor can offer a migration from that specific system because no competitor built it. That trust — earned over a decade — is the foundation Nova is built on.

And the pricing model ($5/user/month with a free community edition) means a 12-person F&B distributor pays $60/month. That's less than a single Odoo module license, less than an ERPNext per-user fee. At that price, Nova doesn't need to be perfect — it needs to be better than the current chaos of spreadsheets and phone calls.

## 5. Visual Design

Visual design tokens (colors, typography, spacing, components, motion) live in `docs/design.md`. If that file does not yet exist, run the Design System skill with image references to generate it before building.
