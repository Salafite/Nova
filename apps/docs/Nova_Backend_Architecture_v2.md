# Nova Backend Architecture v2

## Stack

-   Node.js
-   TypeScript
-   Express/Fastify
-   PostgreSQL
-   Redis
-   JWT

## Layers

Controller -\> Service -\> Repository -\> Database

## Shared Services

-   Authentication
-   RBAC
-   Workflow
-   Notifications
-   Reporting
-   Search
-   Audit
-   File Storage

## Modules

Core, Inventory, Warehouse, Sales, Purchasing, CRM, HR, Manufacturing,
Accounting, Projects, Quality, Maintenance, BI

## API

/api/v1/{module}
