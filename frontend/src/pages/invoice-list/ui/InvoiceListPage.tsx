import { useLoaderData, useRevalidator } from 'react-router';
import { Inbox, Loader2 } from 'lucide-react';

import { InvoiceRow } from '@/entities/invoice';
import { UploadInvoiceDialog } from '@/features/invoice-upload';
import { Button } from '@/shared/ui/button';
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/shared/ui/empty';

import type { loader } from '../api/loader';

export function HydrateFallback() {
  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6 px-5 py-10">
      <div role="status" className="flex justify-center py-10">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
        <span className="sr-only">Loading invoices…</span>
      </div>
    </div>
  );
}

export function InvoiceListPage() {
  const invoices = useLoaderData<typeof loader>();

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6 px-5 py-10">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold">Invoices</h1>
        <UploadInvoiceDialog />
      </div>

      {invoices.length === 0 && (
        <Empty>
          <EmptyHeader>
            <EmptyMedia>
              <Inbox />
            </EmptyMedia>
            <EmptyTitle>No invoices yet</EmptyTitle>
          </EmptyHeader>
        </Empty>
      )}

      {invoices.length > 0 && (
        <ul aria-label="Invoices" className="flex flex-col gap-3">
          {invoices.map((invoice, index) => (
            <li>
              <InvoiceRow key={invoice.id} invoice={invoice} index={index + 1} />
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
          <EmptyTitle>Couldn't load your invoices</EmptyTitle>
          <EmptyDescription>Something went wrong. Please try again.</EmptyDescription>
        </EmptyHeader>
        <Button onClick={retry}>Retry</Button>
      </Empty>
    </div>
  );
}
