import { useLoaderData, useRevalidator } from 'react-router';
import { Inbox, Loader2 } from 'lucide-react';

import { ReviewQueueRow } from '@/entities/invoice';
import { Button } from '@/shared/ui/button';
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/shared/ui/empty';

import type { loader } from '../api/loader';

export function HydrateFallback() {
  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6 px-5 py-10">
      <div role="status" className="flex justify-center py-10">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
        <span className="sr-only">Loading review queue…</span>
      </div>
    </div>
  );
}

export function ReviewQueuePage() {
  const items = useLoaderData<typeof loader>();

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6 px-5 py-10">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold">Review Queue</h1>
        <p className="text-sm text-muted-foreground">{items.length} awaiting review</p>
      </div>

      {items.length === 0 && (
        <Empty>
          <EmptyHeader>
            <EmptyMedia>
              <Inbox />
            </EmptyMedia>
            <EmptyTitle>Nothing waiting for review</EmptyTitle>
            <EmptyDescription>
              New submissions will show up here as employees upload invoices
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      )}

      {items.length > 0 && (
        <ul aria-label="Review queue" className="flex flex-col gap-3">
          {items.map((item) => (
            <li>
              <ReviewQueueRow key={item.id} item={item} />
            </li>
          ))}
        </ul>
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
          <EmptyTitle>Couldn't load the review queue</EmptyTitle>
          <EmptyDescription>Something went wrong. Please try again.</EmptyDescription>
        </EmptyHeader>
        <Button onClick={retry}>Retry</Button>
      </Empty>
    </div>
  );
}
