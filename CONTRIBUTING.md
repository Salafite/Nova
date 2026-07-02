# Contributing to Nova ERP

## Development Setup

1. Clone the repo: `git clone https://github.com/your-org/nova-erp.git`
2. Backend: `cd apps/api && pip install -r requirements.txt`
3. Frontend: `cd apps/web-vue && npm install`
4. Copy `.env.example` to `.env` and fill in your values
5. Start backend: `python main.py` (from `apps/api/`)
6. Start frontend: `npm run dev` (from `apps/web-vue/`)

## Code Style

- Python: Follow PEP 8. Use descriptive names.
- Vue 3: Use Composition API (`<script setup>`). Keep components focused.
- Database: All schema changes go in `database/migrations/` with sequential numbering.

## Pull Request Process

1. Create a branch from `main` named `phase-<number>/<description>`
2. Implement your changes
3. Run the tests
4. Open a PR with a clear description of what changed and why
5. Wait for review before merging

## Reporting Issues

- Bug reports: include steps to reproduce, expected vs actual behavior, and environment info
- Feature requests: describe the problem you're solving, not just the solution
