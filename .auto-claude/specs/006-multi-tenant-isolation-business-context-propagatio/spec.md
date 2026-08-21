# Multi-Tenant Isolation & Business Context Propagation

Add `business_id` columns across all business schema tables, inject tenant context into JWT claims and repository queries, and enforce strict database tenant separation across API and MCP tool calls.

## Rationale
Currently, business tables lack `business_id` columns and tenant scoping. In a multi-tenant or SaaS deployment, one business could inadvertently access or modify data belonging to another tenant.

## User Stories
- As a SaaS distributor customer, I want guaranteed data isolation so that our pricing, customer lists, and financial records are completely inaccessible to other distributors.
- As an AI assistant user, I want tool calls scoped strictly to my organization's business ID without accidental data leakage.

## Acceptance Criteria
- [ ] Schema migration adds NOT NULL `business_id` foreign keys and composite indexes to all business entities
- [ ] FastAPI dependency extracts `business_id` from validated JWT and injects it into every repository query automatically
- [ ] MCP tool handlers enforce tenant filtering on all queries and mutations
- [ ] Cross-tenant data access attempts return 403 Forbidden and trigger a security audit event
