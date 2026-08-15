# Invoice Guard - Backend

The backend is a FastAPI application backed by PostgreSQL and Redis. It can be run either as part of the Docker Compose stack or directly on your machine for local development.

## Stack

- **FastAPI** as the API framework.
- **Pydantic** for request, response, and settings validation.
- **PostgreSQL** as the relational database.
- **Redis** for per-user invoice upload rate limiting and the RQ extraction queue.
- **OpenAI structured outputs** for schema-constrained invoice field extraction.
- **SQLAlchemy** with `asyncpg` for asynchronous ORM and database access.
- **Alembic** for migrations, configured for async engines.
- **Argon2** and **PyJWT** for password hashing and JWT bearer authentication.
- **pytest**, **HTTPX**, and **Testcontainers** for automated testing with real PostgreSQL instances.
- **Ruff** and **mypy** for formatting, linting, and strict type checking.
- **uv** for dependency and virtual environment management.

## Prerequisites

Before getting started, ensure you have the following installed:

- Docker and Docker Compose
- Python 3.13
- [`uv`](https://docs.astral.sh/uv/) for dependency management

## Environment setup

From the repository root, create the environment files:

```sh
cp .env.example .env
cp backend/.env.example backend/.env
```

Update the root `.env` file with your PostgreSQL credentials, then set `OPENAI_API_KEY` in `backend/.env`. The example files also contain the Redis connection, invoice upload, and extraction model settings used by local development.

> **NOTE**
>
> The default PostgreSQL and Redis hosts are intended for a backend process hosted locally. Docker Compose supplies the service host names to its containers.

## Run with Docker Compose

The root `Makefile` provides convenient wrappers around the Docker Compose commands used to manage the stack.

From the repository root, start PostgreSQL and Redis, apply database migrations, and run the backend, extraction worker, and frontend. Use `up-d` to start the same stack in the background:

```sh
make up
make up-d
```

The API will be available at <http://localhost:8000>.

The remaining Make targets manage a running stack:

- `make db` starts only PostgreSQL in the background.
- `make logs` follows logs from all containers.
- `make down` stops the stack and removes its containers and networks.
- `make down-v` also removes its volumes and permanently deletes the local PostgreSQL and Redis data.
- `make help`, which is also the default `make` target, lists the available commands.

The underlying Compose commands are visible in the root `Makefile` if Make is not available on your system.

## Run the backend locally

In this workflow, only the backend process is hosted directly on your machine. PostgreSQL and Redis still run in Docker, so you do not need to install either service locally. Start both containers from the repository root; `compose.yml` publishes them on `localhost:5432` and `localhost:6379`.

```sh
docker compose up -d postgres redis
```

Alternatively, you can use PostgreSQL and Redis servers installed directly on your machine. Ensure PostgreSQL contains the database and user configured in the root `.env` file, then update the corresponding host and port settings if either service does not use the local defaults.

Then install the dependencies, apply migrations, and start FastAPI from the `backend` directory:

```sh
cd backend
uv sync
uv run alembic upgrade head
uv run fastapi dev app/main.py --host 0.0.0.0 --port 8000
```

Start the extraction worker in a second terminal from the `backend` directory:

```sh
uv run rq worker extraction --with-scheduler
```

## Invoice uploads

Authenticated users can upload invoices as multipart form data through `POST /invoices`. The `file` field currently accepts non-empty PDF content whose filename ends in `.pdf`.

Accepted uploads are stored and queued for asynchronous extraction. They return `201` with an invoice ID and usually a `pending` status. The service creates the database record before writing the file. If storage fails, it marks the record as `upload_failed` and returns `503` so the request can be retried safely. If queueing fails, the upload remains accepted but is returned with an `extraction_failed` status.

Upload behavior is configured in `backend/.env`:

| Setting                            | Default           | Purpose                                                 |
| ---------------------------------- | ----------------- | ------------------------------------------------------- |
| `UPLOAD_MAX_BYTES`                 | `10485760`        | Maximum file bytes accepted per upload                  |
| `UPLOAD_RATE_LIMIT`                | `20`              | Valid uploads allowed per authenticated user per window |
| `UPLOAD_RATE_LIMIT_WINDOW_SECONDS` | `60`              | Fixed rate-limit window duration                        |
| `STORAGE_LOCAL_PATH`               | `./data/invoices` | Local directory used to store accepted files            |

Local file storage is intended for development and CI only. Deployments should provide an object-storage adapter through the existing storage interface.

The endpoint can return:

- `400` for empty or otherwise invalid uploads
- `401` when authentication is missing or invalid
- `413` when the file exceeds the configured size limit
- `415` when the declared type, filename extension, or content is not a PDF
- `429` when the authenticated user exhausts the upload limit
- `503` when storage is temporarily unavailable

The raw `POST /invoices` request body is capped before multipart parsing at `UPLOAD_MAX_BYTES` plus 64 KiB for the multipart envelope. This bounds temporary disk and memory use even for unauthenticated or chunked requests.

## Invoice extraction

The RQ worker reads an uploaded PDF, extracts its text layer, and sends that text to the configured OpenAI model for structured extraction. Returned values are checked against the source text before the invoice is saved with an `extracted` status and `high` or `low` confidence. PDFs without a text layer and jobs that exhaust their retries are marked `extraction_failed`.

Authenticated users can retrieve an invoice they own through `GET /invoices/{invoice_id}`. The response contains its current status and, when extraction succeeds, the extracted fields, confidence, and confidence reason. Missing invoices and invoices owned by another user both return `404`.

## Invoice rule evaluation

Once extraction succeeds, the same RQ job evaluates the extracted fields against deterministic policy rules: spending limit, line-item/tax reconciliation, currency allow-list, and two invoice-date checks. Evaluation is skipped entirely when extraction fails.

Every rule always produces a result for an evaluated invoice - `pass`, `fail`, or `not_applicable` - and the full set is persisted to `invoice_rule_results`, replacing any prior results for that invoice so a retried job never duplicates rows.

Rule thresholds are configured in `backend/.env`: `RULE_MAX_EXPENSE_AMOUNT`, `RULE_MAX_EXPENSE_AGE_DAYS`, `RULE_ALLOWED_CURRENCIES`, and `RULE_RECONCILIATION_TOLERANCE`.

## Project structure

```
app/
  api/                  # FastAPI routers + shared dependencies
  core/
    security/           # Password hashing and JWT issuing/decoding
    config.py           # Settings (env-driven)
    queue.py            # RQ queue connection and factory
    rate_limit.py       # Redis-backed fixed-window rate limiter
    storage.py          # Invoice storage interface and local adapter
  database/
    migrations/         # Alembic env + versioned migrations
    repositories/       # Data-access classes, one per aggregate
    models/             # SQLAlchemy ORM models
    base.py             # Declarative base model
    session.py          # Engine, session factories
  queueing/
    jobs/               # Queue-owned job payloads
    extraction.py       # Extraction enqueueing and worker lifecycle
    reconcile.py        # Recovery of stale pending extractions
  schemas/              # Pydantic request/response models
  services/
    extraction/         # Model extraction pipeline
    rules/              # Deterministic policy rule checks and engine
    upload/             # Upload intake and validation
    auth.py             # Authentication use cases
scripts/                # Operational commands, including local user seeding
tests/
  unit/                 # No I/O, collaborators mocked
  integration/          # Real infrastructure; grouped by adapter
  acceptance/           # HTTP scenarios grouped by user-facing capability
```

## Tests

Tests are split into three tiers:

- **Unit:** Verifies one object's behavior without I/O.
- **Integration:** Verifies one real adapter against PostgreSQL.
- **Acceptance:** Verifies user-visible behavior through the HTTP API.

Integration and acceptance tests use Testcontainers to start disposable PostgreSQL and Redis instances. Docker must therefore be running for those tiers and for the complete suite. Test data is isolated between tests.

From the `backend` directory:

```sh
uv run pytest                   # Run all test tiers (requires Docker)
uv run pytest -m unit           # Run the fast unit suite only
uv run pytest -m integration    # Verify real infrastructure adapters
uv run pytest -m acceptance     # Verify behavior through the HTTP boundary
```

Tests use behavior-oriented names beginning with `should_`. Pytest is configured in `pyproject.toml` to collect both `should_*` and conventional `test_*` functions.
