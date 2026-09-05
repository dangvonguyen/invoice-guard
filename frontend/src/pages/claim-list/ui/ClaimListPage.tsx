import { Link, useLoaderData, useRevalidator } from 'react-router';
import { Inbox, Loader2, Plus } from 'lucide-react';

import { ClaimRow } from '@/entities/claim';
import { paths } from '@/shared/config/paths';
import { cn } from '@/shared/lib/utils';
import { Button, buttonVariants } from '@/shared/ui/button';
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/shared/ui/empty';

import type { loader } from '../api/loader';
import { PAGE_SIZE } from '../api/loader';

export function HydrateFallback() {
  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6 px-5 py-10">
      <div role="status" className="flex justify-center py-10">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
        <span className="sr-only">Loading claims…</span>
      </div>
    </div>
  );
}

export function ClaimListPage() {
  const { needsAction, all } = useLoaderData<typeof loader>();
  const hasMore = all.meta !== null && all.claims.length < all.meta.total;
  const isEmpty = needsAction.length === 0 && all.claims.length === 0;

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-8 px-5 py-10">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold">My Claims</h1>
        <Link
          to={paths.newClaim}
          className={cn(buttonVariants({ variant: 'default' }), 'rounded-2xl')}
        >
          <Plus />
          New
        </Link>
      </div>

      {isEmpty && (
        <Empty>
          <EmptyHeader>
            <EmptyMedia>
              <Inbox />
            </EmptyMedia>
            <EmptyTitle>No claims yet</EmptyTitle>
            <EmptyDescription>Submit an expense and it'll show up here.</EmptyDescription>
          </EmptyHeader>
        </Empty>
      )}

      {needsAction.length > 0 && (
        <section className="flex flex-col gap-3">
          <h2 className="text-sm font-medium text-muted-foreground">
            Needs your input ({needsAction.length})
          </h2>
          <ul aria-label="Needs your input" className="flex flex-col gap-3">
            {needsAction.map((claim) => (
              <li key={claim.id}>
                <ClaimRow claim={claim} />
              </li>
            ))}
          </ul>
        </section>
      )}

      {all.claims.length > 0 && (
        <section className="flex flex-col gap-3">
          <h2 className="text-sm font-medium text-muted-foreground">All claims</h2>
          <ul aria-label="All claims" className="flex flex-col gap-3">
            {all.claims.map((claim) => (
              <li key={claim.id}>
                <ClaimRow claim={claim} />
              </li>
            ))}
          </ul>

          {hasMore && (
            <Link
              to={{ search: `?limit=${all.claims.length + PAGE_SIZE}` }}
              preventScrollReset
              className={cn(buttonVariants({ variant: 'outline' }), 'self-center')}
            >
              Load more claims
            </Link>
          )}
        </section>
      )}
    </div>
  );
}

export function ErrorBoundary() {
  const revalidator = useRevalidator();

  function retry() {
    void revalidator.revalidate();
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6 px-5 py-10">
      <Empty>
        <EmptyHeader>
          <EmptyTitle>Couldn't load your claims</EmptyTitle>
          <EmptyDescription>Something went wrong. Please try again.</EmptyDescription>
        </EmptyHeader>
        <Button onClick={retry}>Retry</Button>
      </Empty>
    </div>
  );
}
