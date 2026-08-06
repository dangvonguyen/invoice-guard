# Invoice Guard - Backend

The backend is a FastAPI application backed by PostgreSQL. It can be run either as part of the Docker Compose stack or directly on your machine for local development.

## Stack

- **FastAPI** as the API framework.
- **Pydantic** for request, response, and settings validation.
- **PostgreSQL** as the relational database.
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

Update the root `.env` file with your PostgreSQL credentials.

> **NOTE**
>
> The default `POSTGRES_HOST=localhost` and `POSTGRES_PORT=5432` are intended for a backend process hosted locally. Docker Compose supplies its own host and port values to the containers.

## Run with Docker Compose

The root `Makefile` provides convenient wrappers around the Docker Compose commands used to manage the stack.

From the repository root, start PostgreSQL, apply database migrations, and run the backend with automatic reload. Use `up-d` to start the same stack in the background:

```sh
make up
make up-d
```

The API will be available at <http://localhost:8000>.

The remaining Make targets manage a running stack:

- `make db` starts only PostgreSQL in the background.
- `make logs` follows logs from all containers.
- `make down` stops the stack and removes its containers and networks.
- `make down-v` also removes its volumes and permanently deletes the local PostgreSQL data.
- `make help`, which is also the default `make` target, lists the available commands.

The underlying Compose commands are visible in the root `Makefile` if Make is not available on your system.

## Run the backend locally

In this workflow, only the backend process is hosted directly on your machine. PostgreSQL still runs in Docker, so you do not need to install PostgreSQL locally. Start the
database container from the repository root; `compose.yml` publishes it on `localhost:5432`.

```sh
make db
```

Alternatively, you can use a PostgreSQL server installed directly on your machine. Ensure it contains the database and user configured in the root `.env` file, and update `POSTGRES_HOST` and `POSTGRES_PORT` if it is not listening on `localhost:5432`.

Then install the dependencies, apply migrations, and start FastAPI from the `backend` directory:

```sh
cd backend
uv sync
uv run alembic upgrade head
uv run fastapi dev app/main.py --host 0.0.0.0 --port 8000
```

## Project structure

```
app/
  api/                  # FastAPI routers + shared dependencies
  core/
    config.py           # Settings (env-driven)
    security/           # Password hashing and JWT issuing/decoding
  database/
    migrations/         # Alembic env + versioned migrations
    repositories/       # Data-access classes, one per aggregate
    models/             # SQLAlchemy ORM models
    base.py             # Declarative base model
    session.py          # Engine, session factories
  schemas/              # Pydantic request/response models
  services/             # Application use cases and collaborator protocols
scripts/                # Operational commands, including local user seeding
tests/
  unit/                 # No I/O, collaborators mocked
  integration/          # Real Postgres, single adapter, no HTTP
  acceptance/           # Real Postgres, real app, through HTTP
```

## Tests

Tests are split into three tiers:

- **Unit:** Verifies one object's behavior without I/O.
- **Integration:** Verifies one real adapter against PostgreSQL.
- **Acceptance:** Verifies user-visible behavior through the HTTP API.

Integration and acceptance tests use Testcontainers to start a disposable PostgreSQL instance. Docker must therefore be running for those tiers and for the complete suite. Test data is isolated by a transaction that is rolled back after every test.

From the `backend` directory:

```sh
uv run pytest                   # Run all test tiers (requires Docker)
uv run pytest -m unit           # Run the fast unit suite only
uv run pytest -m integration    # Verify real infrastructure adapters
uv run pytest -m acceptance     # Verify behavior through the HTTP boundary
```

Tests use behavior-oriented names beginning with `should_`. Pytest is configured in `pyproject.toml` to collect both `should_*` and conventional `test_*` functions.
