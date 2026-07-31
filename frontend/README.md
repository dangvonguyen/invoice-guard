# Invoice Guard - Frontend

The frontend is a React application built with Vite, TypeScript, and Tailwind CSS. It can be run either as part of the Docker Compose stack or directly on your machine for local development.

## Prerequisites

Before getting started, ensure you have the following installed:

- Docker and Docker Compose
- Node.js 24
- [`pnpm`](https://pnpm.io/)

## Environment setup

From the repository root, create the frontend environment file:

```sh
cp frontend/.env.example frontend/.env
```

The default `VITE_API_URL=http://localhost:8000` connects the frontend to the locally exposed backend API.

## Run with Docker Compose

From the repository root, start the full development stack:

```sh
make up
```

Use `make up-d` to run the stack in the background. The frontend will be available at <http://localhost:5173>.

## Run the frontend locally

First, ensure the backend is running at <http://localhost:8000>. Then install the dependencies and start the Vite development server:

```sh
cd frontend
pnpm install
pnpm dev
```

Alternatively, run `make run-frontend-local` from the repository root after installing the dependencies.

## Available commands

Run these commands from the `frontend` directory:

- `pnpm dev` starts the development server.
- `pnpm build` creates a production build.
- `pnpm preview` previews the production build locally.
- `pnpm lint` checks the code with ESLint.
- `pnpm lint:fix` fixes supported ESLint issues.
- `pnpm format` formats the code with Prettier.
- `pnpm format:check` checks code formatting.
- `pnpm check` runs linting, formatting checks, and a production build.
