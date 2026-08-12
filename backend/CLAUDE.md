# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**Current phase: Core/MVP.** Authentication, upload, extraction, rule engine, RAG exception path, and review queue.

## Development Commands

Run from the `backend/` directory unless noted.

```sh
# Setup and runtime
uv sync
uv run alembic upgrade head
uv run fastapi dev app/main.py

# Tests
uv run pytest  # Requires Docker: testcontainers spins up PG/Redis
uv run pytest -m unit
uv run pytest -m integration
uv run pytest -m acceptance
uv run pytest path/to/test_file.py::test_name
uv run pytest -k "key"

# Code quality
uv run ruff check .
uv run ruff format .
uv run mypy app tests --strict
```

From the repo root, `make up`/`make up-d` bring up the full Docker Compose stack; `make db` starts just Postgres and Redis for the hybrid workflow (containers for infra, `fastapi dev` on host).

## Architecture

```
app/
  api/
    routers/           # HTTP endpoints
    deps.py            # dependency wiring
    middleware.py      # raw ASGI middleware
    router.py          # router aggregation
  core/
    config.py          # Pydantic settings
    security/          # password hashing and JWT
    rate_limit.py      # Redis-backed fixed-window rate limiting
    storage.py         # storage adapters
    logging.py         # structured logs and correlation context
  database/
    models/            # SQLAlchemy ORM
    repositories/      # persistence adapters
    migrations/        # Alembic migration
    session.py         # database session dependencies
  services/            # use-case orchestration
  schemas/             # Pydantic request/response models
  workers/             # background-job entry points
tests/
  unit/
  integration/
  acceptance/
```

**Two async session dependencies** (`api/deps.py`): `SessionDep` auto-commits / rolls back around the request (default); `SessionManualDep` leaves transaction control the app code, used where a row must survive a later failure in the same request.
