---
paths:
  - "**/src/**/*.tsx"
  - "**/src/**/*.ts"
---
# Feature-Sliced Design (FSD) Architecture

> This file extends [react/coding-style.md](./coding-style.md) with the project's frontend layering rules.

## Layer Stack

Top → bottom, strict unidirectional imports — a layer can only import from layers below it:

```
src/
├── app/                          # composition root — no business logic
│   ├── providers/
│   │   ├── router.tsx
│   │   ├── store.tsx
│   │   └── query-client.tsx
│   ├── styles/
│   │   └── global.css
│   └── index.tsx
│
├── pages/                        # route-level compositions
│   ├── invoice-list/
│   │   ├── ui/
│   │   │   └── InvoiceListPage.tsx
│   │   ├── api/
│   │   │   ├── loader.ts
│   │   │   └── action.ts
│   │   └── index.ts               # public API — re-exports only
│   ├── invoice-detail/
│   │   ├── ui/
│   │   │   └── InvoiceDetailPage.tsx
│   │   ├── api/
│   │   │   └── loader.ts
│   │   └── index.ts
│   └── user-profile/
│       ├── ui/
│       │   └── UserProfilePage.tsx
│       ├── api/
│       │   ├── loader.ts
│       │   └── action.ts
│       └── index.ts
│
├── widgets/                      # composite, reusable UI blocks (combine features+entities)
│   ├── invoice-summary-card/
│   │   ├── ui/
│   │   │   └── InvoiceSummaryCard.tsx
│   │   └── index.ts
│   └── user-header/
│       ├── ui/
│       │   └── UserHeader.tsx
│       └── index.ts
│
├── features/                     # user-triggered actions/use-cases
│   ├── create-invoice/
│   │   ├── ui/
│   │   │   └── CreateInvoiceForm.tsx
│   │   ├── model/
│   │   │   └── useCreateInvoice.ts
│   │   ├── api/
│   │   │   └── createInvoiceRequest.ts   # only if orchestration crosses entities
│   │   └── index.ts
│   └── update-user-email/
│       ├── ui/
│       │   └── UpdateEmailForm.tsx
│       ├── model/
│       │   └── useUpdateEmail.ts
│       └── index.ts
│
├── entities/                     # business domain objects
│   ├── user/
│   │   ├── ui/
│   │   │   ├── UserCard.tsx
│   │   │   └── UserAvatar.tsx
│   │   ├── model/
│   │   │   ├── types.ts           # User, UserRole
│   │   │   ├── store.ts           # userSlice / userAtom
│   │   │   └── selectors.ts
│   │   ├── api/
│   │   │   ├── getUser.ts
│   │   │   ├── updateUser.ts
│   │   │   └── dto.ts             # DTO -> domain type
│   │   ├── lib/
│   │   │   └── formatUserName.ts
│   │   └── index.ts               # public API
│   └── invoice/
│       ├── ui/
│       │   └── InvoiceRow.tsx
│       ├── model/
│       │   ├── types.ts           # Invoice, InvoiceStatus
│       │   └── store.ts
│       ├── api/
│       │   ├── getInvoice.ts
│       │   ├── listInvoices.ts
│       │   ├── createInvoice.ts
│       │   └── dto.ts
│       ├── lib/
│       │   └── calculateTotal.ts
│       └── index.ts
│
└── shared/                       # entity-agnostic infrastructure
    ├── api/
    │   ├── client.ts              # axios/fetch instance
    │   ├── interceptors.ts
    │   └── endpoints.ts           # base URL config, no domain types
    ├── ui/
    │   ├── Button.tsx
    │   ├── Input.tsx
    │   └── Modal.tsx
    ├── lib/
    │   ├── formatDate.ts
    │   └── debounce.ts
    ├── config/
    │   └── env.ts
    └── types/
        └── common.ts               # Pagination<T>, ApiError, etc. — no domain-specific types
```

## Rules

- Import direction is `app → pages → widgets → features → entities → shared`. `entities/invoice` cannot import from `entities/user` directly — cross-entity composition happens in `features` or `widgets`.
- Every slice exposes a single `index.ts` public API. Internal files (`dto.ts`, `store.ts`) are never imported directly from outside the slice — this is what makes slices swappable/testable in isolation.
- `shared/` has zero domain knowledge. `shared/api/client.ts` never imports `User` or `Invoice` types.
- Segment names (`ui`, `model`, `api`, `lib`, `config`) are fixed vocabulary. Don't invent `helpers/` or `utils/` inside a slice — it goes in `lib/`.

## Data Loading & Actions (React Router)

Pages use React Router's loader/action data mode, not `useEffect`-fetched local state or direct API calls in submit handlers.

- Fetch-on-entry → `api/loader.ts` exporting `loader`; submit → `api/action.ts` exporting `action`. Both re-export from the slice's `index.ts` alongside `Component`, picked up by the lazy route module.
- `loader`/`action` call entity `api/` functions, never `apiClient`/`fetch` directly.
- Components read data via `useLoaderData()`, never `useEffect` + `useState`. Mutations go through `<Form>`/`useFetcher()`, never a direct call in `onSubmit`.
- Pending/error UI comes from `useNavigation()`/`useFetcher().state`/`ErrorBoundary`, not local `isLoading`/`hasError` state.
- The `action` lives on the page/route that owns the URL — features supply `ui`/`model` only, never their own `action`.
