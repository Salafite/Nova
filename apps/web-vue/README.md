# Nova ERP — Frontend

Vue 3 SPA built with Vite, Pinia, and Vue Router (hash mode).

## Quick Start

```bash
npm install
npm run dev        # dev server on port 5173, proxies /api → localhost:8070
npm run build      # production build to dist/
npm test           # Vitest unit tests
npx playwright test  # E2E tests
```

## Stack

- **Vue 3** (Composition API, `<script setup>`)
- **Vite** (build tool)
- **Pinia** (state management)
- **Vue Router** (hash history, auth guards)
- **Axios** (API client, JWT interceptor)
- **Playwright** (E2E tests)
- **Vitest** (unit tests)

## Project Structure

```
src/
├── api/          # Axios client, interceptors
├── assets/       # Static assets
├── components/   # Shared components (AppSidebar, AppTopBar, etc.)
├── composables/  # useI18n, useToast, etc.
├── layouts/      # AppLayout (sidebar + grid modes)
├── locales/      # en.json, ar.json — i18n dictionaries
├── router/       # Route definitions, auth guard
├── stores/       # Pinia stores (auth, nav, settings, etc.)
├── utils/        # Utility functions
├── views/        # Page components organized by domain
├── __tests__/    # Unit tests
└── style.css     # Global styles
```

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE` | `http://localhost:8070` | Backend API URL |

See [../DEPLOYMENT.md](../DEPLOYMENT.md) for full deployment instructions.
