# CLAUDE.md — backend

FastAPI service. Run every command below from `backend/`. Repo-wide rules live in the root `CLAUDE.md`.

**Current phase: Core/MVP** — auth, upload, extraction, rule engine, review queue, decisions.

## Commands

```sh
uv sync
uv run alembic upgrade head
uv run fastapi dev app/main.py
uv run rq worker extraction --with-scheduler   # extraction/rules worker

uv run pytest
uv run pytest -m unit
uv run pytest -m integration
uv run pytest -m acceptance
uv run ruff check . && uv run ruff format .
uv run mypy app tests --strict
```

## Layering

```
app/
  api/
    routers/      HTTP endpoints, one module per resource
    deps/         Annotated dependency aliases, one module per resource + sessions.py
    handlers.py   domain/HTTP exceptions -> response envelope
    middleware.py raw ASGI (request logging, body-size limit)
  core/           config, errors, logging, redis, queue, rate_limit, storage, security/
  database/       models/, repositories/ (one per aggregate), migrations/, session.py
  services/       use-case orchestration (upload, extraction, rules, review, policies, auth)
  queueing/       jobs/ payloads + invoice_processing.py pipeline + reconcile.py
  schemas/        Pydantic request/response models
```

Direction of dependency: `routers -> services -> repositories`. Routers do HTTP concerns only; business logic lives in services; all SQL lives in repositories. Services never import FastAPI.

## Conventions

**Dependencies.** Every dependency is exported from `app.api.deps` as an `Annotated` alias (`CurrentUser`, `CurrentFinanceReviewer`, …). Add new ones to the matching `deps/<resource>.py` and re-export from `deps/__init__.py`; routers import from `app.api.deps` only.

**Sessions.** `SessionDep` commits/rolls back around the request — the default. `SessionManualDep` hands transaction control to the app code; use it only when a row must survive a later failure in the same request (e.g. `InvoiceRepository.create_processing` commits before the storage write so intake evidence is never rolled back).

**Errors.** Raise `DomainError` subclasses from `app.core.errors` (`NotFoundError`, `ForbiddenError`, `UnauthorizedError`, `ValidationError`) or define a new subclass with its own `code`/`status_code` next to the service that raises it. `register_exception_handlers` maps them to the envelope — services stay transport-agnostic and must not raise `HTTPException`.

**Responses.** Every route returns `ResponseEnvelope[Data, Meta]` (`app/schemas/envelope.py`); list routes carry `PaginationMeta`. Errors a *dependency* raises are invisible to the generated schema, so declare them via the shared blocks in `app/api/openapi.py`.

**Config.** All settings come from `get_settings()` (Pydantic settings, env-driven). No literals for limits, thresholds, or timeouts in code.

## Tests

Three tiers, selected by marker; keep new tests in the tier that matches what they prove.

- `unit/` — one object, no I/O, collaborators mocked.
- `integration/` — one real adapter against real PostgreSQL/Redis, no HTTP layer.
- `acceptance/` — real app through the HTTP boundary, grouped by user-facing capability, using fully wired objects.

Test functions are behaviour sentences named `should_...` (pytest is configured to collect both `should_*` and `test_*`). Shared fixtures: `tests/conftest.py`, per-tier `conftest.py`; helpers and fixed constants in `tests/support/` (`create_user`, `pdf_bytes`). Integration and acceptance tiers need Docker.
