---
paths:
  - "**/src/**/*.tsx"
  - "**/src/**/*.ts"
---
# Feature-Sliced Design (FSD) Architecture

Extends [react/coding-style.md](./coding-style.md) with frontend layering rules.

## Layers

Import direction is strictly one-way: `app → pages → widgets → features → entities → shared`. A slice imports only from layers **below** it.

| Layer | Purpose | Slice name |
|-------|---------|------------|
| `app` | Composition root: providers, router, store, global styles. No business logic. | — |
| `pages` | Route-level compositions. | route noun: `checkout`, `user-list`, `user-detail` |
| `widgets` | Composite, reusable UI blocks (features + entities combined). | noun for the block: `app-header`, `user-summary-card` |
| `features` | User-triggered actions / use-cases. | verb first: `auth-by-email`, `update-user-email` |
| `entities` | Business domain objects. | singular domain noun: `user`, `order`, `session` |
| `shared` | Entity-agnostic infrastructure. Zero domain knowledge. | — |

## Slice internals

A slice is a folder of **segments**, each naming a *purpose*, not a kind of file:

- `ui/` — components
- `model/` — `types.ts` (camelCase app models), `mapper.ts` (`toUser(dto)`, incl. date strings → `Date`), `store.ts`, `selectors.ts`
- `api/` — `types.ts` (snake_case DTOs mirroring the backend), one function per endpoint (`getUser.ts`); functions return **models**, never DTOs
- `lib/` — pure helpers (`formatUserName.ts`)
- `config/` — constants, env
- `index.ts` — the slice's only public API; re-exports only

Never create `helpers/`, `utils/`, `components/`, `hooks/`, or `types/` segments. Custom segments are allowed only in `app/` and `shared/`, and only when they name a real purpose.

## Rules

- **No same-layer imports.** No page imports a page, no feature imports a feature, `entities/order` does not import `entities/user`. Exception: `app` and `shared` segments may import each other freely, but never a layer above.
- **Cross-entity composition** belongs in `features` or `widgets`. If an entity genuinely must reference another, use the explicit `@x` cross-import notation (`@/entities/<a>/@x/<b>`) — never reach into another slice's internals.
- **Only `index.ts` is importable from outside a slice.** Internal files (`mapper.ts`, `store.ts`, …) stay private; this is what makes slices swappable and testable in isolation. Exception: `shared/ui` and `shared/lib` expose one index file per component/util (no shared barrel), so an unused primitive never drags its dependencies into the bundle.
- **`shared/` has zero domain knowledge.** `shared/api/client.ts` never imports a domain type; `shared/api/types.ts` holds only transport-level types (`ApiError`, `Envelope<T>`, `Pagination<T>`).
- **DTO ↔ model split.** `api/types.ts` = snake_case DTOs; `model/types.ts` = camelCase app models; `model/mapper.ts` converts between them. Loaders and components consume models only.

## Naming

- **Folders** (slices and segments) are kebab-case: `user-summary-card`, `auth-by-email`.
- **React component files** are PascalCase, matching the export: `UserCard.tsx`, `CheckoutPage.tsx`. The `Page`/`Form` suffix is required so the file self-describes in editor tabs and imports.
- **Other modules** (hooks, request functions, mappers, selectors) are camelCase: `useUpdateUserEmail.ts`, `getUser.ts`.
- **Fixed-role modules** keep their canonical lowercase name: `index.ts`, `types.ts`, `mapper.ts`, `store.ts`, `selectors.ts`, `loader.ts`, `action.ts`.
- **Generated primitives** in `shared/ui/` keep the generator's convention (e.g. shadcn → kebab-case); regenerate, never hand-rename.
- A name should still make sense with its folder context stripped: `UserListPage` is good, a bare `Page` / `index` component is not.

## Data loading & actions (React Router)

Pages use React Router's loader/action data mode — never `useEffect`-fetched state or direct API calls in submit handlers.

- Fetch-on-entry → `api/loader.ts` exporting `loader`; submit → `api/action.ts` exporting `action`. Both re-export from the slice's `index.ts` alongside `Component`.
- `loader`/`action` call entity `api/` functions, never `apiClient`/`fetch` directly.
- Components read data via `useLoaderData()`; mutations go through `<Form>` / `useFetcher()`, never a direct call in `onSubmit`.
- Pending/error UI comes from `useNavigation()` / `useFetcher().state` / `ErrorBoundary`, not local `isLoading` / `hasError` state.
- The `action` lives on the page/route that owns the URL — features supply `ui` / `model` only.
