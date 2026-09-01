# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Agent skills

### Issue tracker

Issues live in GitHub Issues (repo: dangvonguyen/invoice-guard). See `docs/agents/issue-tracker.md`.

### Triage labels

Default canonical labels: needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout (root CONTEXT.md + docs/adr/). See `docs/agents/domain.md`.

### Technology Stack

- **Backend:** Python, FastAPI, SQLAlchemy, PostgreSQL
- **Storage:** S3-compatible object storage
- **Infrastructure:** Redis where appropriate for rate limiting and ephemeral state
- **Frontend:** React, TypeScript, Vite
- **Frontend architecture:** Feature-Sliced Design
- **API contract:** OpenAPI with generated TypeScript types

## Layout

```
backend/    FastAPI service (Python 3.13, uv)   — see backend/CLAUDE.md
frontend/   React SPA (Vite, pnpm)              — see frontend/CLAUDE.md
compose.yml Postgres, Redis, api, worker, web
Makefile    Docker Compose wrappers
```

Work inside the app you are changing; each has its own `CLAUDE.md` with the conventions for that side.

## API contract

- The API is mounted under `root_path` `/api` (`API_ROOT`). Vite proxies `/api` to the backend in dev.
- Every response uses the shared envelope: `{ data, error, meta, success }`. `error` is `{ code, message, details }`; `meta` is `{ total, offset, limit }` on list routes.
- `frontend/api/openapi.yml` is the exported FastAPI schema. After changing any request/response model, re-export it with `poe openapi:export` in `backend/`, then run `pnpm gen:api` in `frontend/` to regenerate `src/shared/api/schema.d.ts` (that file is generated — never hand-edit it).

## Quality gates

CI (`.github/workflows/ci.yml`) runs, and changes are expected to pass locally before commit:

- backend: `ruff check .`, `ruff format --check .`, `mypy app tests`, `pytest`
- frontend: `pnpm lint`, `pnpm format:check`, `tsc -b`, `vite build`
- a Compose smoke test hitting `/api/health/live` and the web app

`prek` (pre-commit) runs ruff, eslint, and prettier on commit and mypy on push; hooks are configured in `.pre-commit-config.yaml`.
