# CLAUDE.md — frontend

React 19 + Vite SPA, Feature-Sliced Design. Run every command below from `frontend/`. Repo-wide rules live in the root `CLAUDE.md`.

## Commands

```sh
pnpm install
pnpm dev                 # needs the backend at :8000 (Vite proxies /api)
pnpm test                # vitest + jsdom + MSW
pnpm check               # lint + format:check + build — run before committing
pnpm gen:api             # regenerate src/shared/api/schema.d.ts from api/openapi.yml
```

## Layers

`app → pages → widgets → features → entities → shared`. A slice may import only from layers **below** it, never sideways within a layer and never upward.

```
src/
  app/        router, AppLayout, global styles
  pages/      route modules
  widgets/    composite UI
  features/   user actions
  entities/   domain nouns: api/, model/, lib/, ui/
  shared/     api client, config (env, paths), lib, ui primitives (shadcn)
```

Every slice exposes a public API through its `index.ts`; cross-slice imports go through `@/<layer>/<slice>` and use the `@/` alias. Reaching into another slice's internals (`@/entities/<slice>/model/mapper`) is not allowed — relative imports are for within-slice files only.

## Conventions

**Routing.** Routes are declared in `src/app/router/router.tsx` with `lazy: () => import('@/pages/<slice>')`, and paths come from `shared/config/paths.ts` — never inline path strings. A page's `index.ts` exports the route module contract: `Component`, `ErrorBoundary`, `HydrateFallback`, plus `loader`/`action` from `./api/`. Data fetching belongs in loaders/actions, not in effects.

**API calls.** One function per endpoint in `entities/<slice>/api/`. Each uses `apiClient` (openapi-fetch, typed from `schema.d.ts`, injects the bearer token), unwraps the response with `unwrapEnvelope`, and translates failures into named error classes (`UnauthenticatedError`, `NotFoundError`, `DecisionConflictError`) rather than leaking status codes to callers.

**DTO ↔ model.** `api/types.ts` holds snake_case DTOs mirroring the backend; `model/types.ts` holds camelCase app models; `model/mapper.ts` converts (`toInvoice`, `toCurrentUser`), including date strings → `Date`. Components consume models only.

**Auth.** The access token lives in the zustand `useAuthStore` (in memory, not persisted). Loaders must not read it directly — use `requireCurrentUser` (redirects to `/login`), `resolveCurrentUser` (returns `null` for a signed-out visitor), or `requireRole` (redirects to `/login`, then to the user's own landing page if their role doesn't match) from `@/entities/user`.

**Styling.** Tailwind v4 + shadcn primitives in `shared/ui/` (generated — regenerate rather than hand-edit). Compose classes with `cn()` from `shared/lib/utils`.

**Lint rules that shape code.** `eqeqeq`, inline `import type`, `simple-import-sort` groups (react/externals → `@/` → parent → sibling), unused vars must be `_`-prefixed. `pnpm lint` runs with `--max-warnings=0`.

## Tests

Vitest + Testing Library, colocated as `*.test.ts(x)` next to the unit under test. HTTP is stubbed at the network boundary with MSW (`tests/mocks/handlers.ts`, `tests/mocks/server.ts`, wired in `tests/setup.ts`) — do not mock `apiClient` or the entity `api/` functions. Query by role/label as a user would, and drive interaction through `@testing-library/user-event`.
