# Invoice Guard - Backend

The backend is a FastAPI application backed by PostgreSQL. It can be run either as part of the Docker Compose stack or directly on your machine for local development.

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

## Tests

From the `backend` directory, run:

```sh
uv run pytest
```
