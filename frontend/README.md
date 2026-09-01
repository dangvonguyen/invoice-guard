# Invoice Guard — Frontend

React SPA built with Vite, TypeScript, and Tailwind CSS, organized by Feature-Sliced Design. Run it as part of the Docker Compose stack — see the [root README](../README.md) for prerequisites, environment files, and the `docker compose` workflow — or directly on your machine as described below.

## Run the frontend on your machine

Ensure the backend is running at <http://localhost:8000> (see [`backend/README.md`](../backend/README.md)), then from the `frontend` directory:

```sh
cd frontend
pnpm install
pnpm dev
```

The dev server runs at <http://localhost:5173> and proxies `/api` to the backend. `VITE_API_URL` in `frontend/.env` (default `http://localhost:8000`) points it at the API. Do not set it to the Compose service name `api` — that hostname does not resolve when Vite runs on the host.

## Architecture

Layers run `app → pages → widgets → features → entities → shared`; a slice may import only from layers below it. `api/openapi.yml` is the exported FastAPI schema — after a backend model change, re-export it and run `pnpm gen:api`. See [`CLAUDE.md`](CLAUDE.md) for the full conventions.
