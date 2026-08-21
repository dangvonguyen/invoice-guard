import type { ReactNode } from 'react';
import { Link, useLoaderData, useRevalidator } from 'react-router';
import { ArrowLeft, FileWarning, Loader2 } from 'lucide-react';

import {
  DecisionCard,
  type InvoiceDetailResponse,
  invoiceStatusBadgeVariant,
  invoiceStatusLabel,
  InvoiceSummaryCard,
} from '@/entities/invoice';
import { paths } from '@/shared/config/paths';
import { Badge } from '@/shared/ui/badge';
import { Button } from '@/shared/ui/button';
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/shared/ui/empty';

import type { loader } from '../api/loader';

export function HydrateFallback() {
  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6 px-5 py-10">
      <div role="status" className="flex justify-center py-10">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
        <span className="sr-only">Loading invoice…</span>
      </div>
    </div>
  );
}

export function InvoiceDetailPage() {
  const result = useLoaderData<typeof loader>();
  const revalidator = useRevalidator();

  function refetch() {
    void revalidator.revalidate();
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6 px-5 py-10">
      <BackToInvoiceList />

      {result.kind === 'not_found' && (
        <Empty>
          <EmptyHeader>
            <EmptyMedia>
              <FileWarning />
            </EmptyMedia>
            <EmptyTitle>Invoice not found</EmptyTitle>
          </EmptyHeader>
        </Empty>
      )}

      {result.kind === 'error' && (
        <Empty>
          <EmptyHeader>
            <EmptyTitle>Couldn't load this invoice</EmptyTitle>
            <EmptyDescription>Something went wrong. Please try again.</EmptyDescription>
          </EmptyHeader>
          <Button onClick={refetch}>Retry</Button>
        </Empty>
      )}

      {result.kind === 'ok' && <InvoiceDetailContent invoice={result.invoice} />}
    </div>
  );
}

export function BackToInvoiceList() {
  return (
    <Link
      to={paths.invoices}
      className="inline-flex w-fit items-center gap-1 text-sm text-muted-foreground transition-colors hover:text-foreground"
    >
      <ArrowLeft className="size-4" aria-hidden="true" />
      Back to invoices
    </Link>
  );
}

function InvoiceDetailContent({ invoice }: { invoice: InvoiceDetailResponse }) {
  return (
    <>
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl leading-none font-semibold tracking-tight">Invoice</h1>
        <Badge variant={invoiceStatusBadgeVariant(invoice.status)}>
          {invoiceStatusLabel(invoice.status)}
        </Badge>
      </div>

      {invoice.status === 'processing' && (
        <StatusNotice>Still processing your invoice.</StatusNotice>
      )}

      {invoice.status === 'processing_error' && (
        <StatusNotice>We couldn't process this invoice.</StatusNotice>
      )}

      {invoice.invoice_summary !== null && <InvoiceSummaryCard summary={invoice.invoice_summary} />}

      {invoice.status === 'awaiting_review' && invoice.decision === null && (
        <StatusNotice>Awaiting review. You'll see the outcome here once it's decided.</StatusNotice>
      )}

      {invoice.decision !== null && <DecisionCard decision={invoice.decision} />}
    </>
  );
}

function StatusNotice({ children }: { children: ReactNode }) {
  return (
    <p className="rounded-xl bg-card p-4 text-sm text-muted-foreground ring-1 ring-foreground/10 text-center">
      {children}
    </p>
  );
}
