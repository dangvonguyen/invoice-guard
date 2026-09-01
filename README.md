# Invoice Guard

Expense-invoice intake and review: employees submit invoices, a deterministic rule engine flags policy concerns, and finance reviewers decide.

## Repository layout

| Path                | What it is                                                                           |
| ------------------- | ------------------------------------------------------------------------------------ |
| `backend/`          | FastAPI service. See [`backend/README.md`](backend/README.md).                       |
| `frontend/`         | React SPA. See [`frontend/README.md`](frontend/README.md).                           |
| `compose.yml`       | Shared service definitions: `postgres`, `redis`, `migrator`, `api`, `worker`, `web`. |
| `compose.local.yml` | Local-dev overlay: source sync, published ports, MinIO object storage.               |
| `compose.prod.yml`  | Production overlay: built `prod` images, restart policies, managed S3.               |
| `docs/`             | Architecture decision records (`docs/adr/`) and agent playbooks (`docs/agents/`).    |

## Prerequisites

- Docker and Docker Compose — to run the full stack.
- Python 3.13 and [`uv`](https://docs.astral.sh/uv/) — only to run the backend directly on your machine.
- Node.js 24 and [`pnpm`](https://pnpm.io/) — only to run the frontend directly on your machine.

## Environment setup

From the repository root, create the environment files and edit as needed:

```sh
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

> The default `POSTGRES_HOST` / `REDIS_HOST` of `localhost` target a backend process running on your machine. Docker Compose overrides them with service hostnames for its own containers.

## Run the full stack with Docker Compose

`compose.yml` holds only the shared service definitions; every invocation pairs it with one overlay. Export `COMPOSE_FILE` once so the plain `docker compose` commands below pick up both files:

```sh
export COMPOSE_FILE=compose.yml:compose.local.yml
```

Build and start services. Add `-d` to run in the background:

```sh
docker compose up --build
```

The API is served at <http://localhost:8000> and the web app at <http://localhost:5173>.

For an edit-reload loop, run `docker compose watch` instead of `up`: it starts the stack and then syncs changes under `backend/` and `frontend/` into the running containers. A `pyproject.toml` or `package.json` change rebuilds the affected image.

Other commands, with the stack already running:

| Command                               | Effect                                                                             |
| ------------------------------------- | ---------------------------------------------------------------------------------- |
| `docker compose up -d postgres redis` | Start only PostgreSQL and Redis, in the background.                                |
| `docker compose logs -f`              | Follow logs from all containers.                                                   |
| `docker compose down`                 | Stop the stack; remove its containers and networks.                                |
| `docker compose down -v`              | Also remove volumes — permanently deletes local PostgreSQL, Redis, and MinIO data. |

## Run a production-style stack

Swap the overlay for built `prod` images, restart policies, and managed S3 storage (put the `STORAGE_S3_*` settings in `backend/.env`):

```sh
docker compose -f compose.yml -f compose.prod.yml up -d --build
```
