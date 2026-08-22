import type { ReactNode } from 'react';
import { Link, useLoaderData, useRevalidator, useRouteError } from 'react-router';
import { ArrowLeft, FileWarning, Loader2 } from 'lucide-react';

import {
  DecisionCard,
  EmployeeIdentityBlock,
  ExtractedFieldsTable,
  type InvoiceDetail,
  invoiceStatusBadgeVariant,
  invoiceStatusLabel,
  InvoiceSummaryCard,
  NotFoundError,
  type ReviewerInvoiceDetail,
  ReviewFlagList,
} from '@/entities/invoice';
import { DecisionForm } from '@/features/review-decision';
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
  const invoice = useLoaderData<typeof loader>();
  const isReviewer = invoice.view === 'reviewer';

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6 px-5 py-10">
      <BackLink
        to={isReviewer ? paths.reviewQueue : paths.invoices}
        label={isReviewer ? 'Back to review queue' : 'Back to invoices'}
      />
      <InvoiceDetailContent invoice={invoice} />
    </div>
  );
}

export function ErrorBoundary() {
  const error = useRouteError();
  const revalidator = useRevalidator();

  function retry() {
    void revalidator.revalidate();
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6 px-5 py-10">
      <BackLink to={paths.invoices} label="Back to invoices" />

      {error instanceof NotFoundError ? (
        <Empty>
          <EmptyHeader>
            <EmptyMedia>
              <FileWarning />
            </EmptyMedia>
            <EmptyTitle>Invoice not found</EmptyTitle>
          </EmptyHeader>
        </Empty>
      ) : (
        <Empty>
          <EmptyHeader>
            <EmptyTitle>Couldn't load this invoice</EmptyTitle>
            <EmptyDescription>Something went wrong. Please try again.</EmptyDescription>
          </EmptyHeader>
          <Button onClick={retry}>Retry</Button>
        </Empty>
      )}
    </div>
  );
}

function BackLink({ to, label }: { to: string; label: string }) {
  return (
    <Link
      to={to}
      className="inline-flex w-fit items-center gap-1 text-sm text-muted-foreground transition-colors hover:text-foreground"
    >
      <ArrowLeft className="size-4" aria-hidden="true" />
      {label}
    </Link>
  );
}

function InvoiceDetailContent({ invoice }: { invoice: InvoiceDetail | ReviewerInvoiceDetail }) {
  if (invoice.view === 'reviewer') {
    return <ReviewerInvoiceDetailContent invoice={invoice} />;
  }

  return <EmployeeInvoiceDetailContent invoice={invoice} />;
}

function EmployeeInvoiceDetailContent({ invoice }: { invoice: InvoiceDetail }) {
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

      {invoice.summary !== null && <InvoiceSummaryCard summary={invoice.summary} />}

      {invoice.status === 'awaiting_review' && invoice.decision === null && (
        <StatusNotice>Awaiting review. You'll see the outcome here once it's decided.</StatusNotice>
      )}

      {invoice.decision !== null && <DecisionCard decision={invoice.decision} />}
    </>
  );
}

function ReviewerInvoiceDetailContent({ invoice }: { invoice: ReviewerInvoiceDetail }) {
  return (
    <>
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl leading-none font-semibold tracking-tight">Invoice</h1>
        <Badge variant={invoiceStatusBadgeVariant(invoice.status)}>
          {invoiceStatusLabel(invoice.status)}
        </Badge>
      </div>

      <EmployeeIdentityBlock employee={invoice.submittedBy} />

      <ExtractedFieldsTable
        fields={invoice.extractedFields}
        confidence={invoice.confidence}
        confidenceReason={invoice.confidenceReason}
      />

      <ReviewFlagList flags={invoice.reviewFlags} />

      {invoice.decision !== null && <DecisionCard decision={invoice.decision} />}
      {invoice.decision === null && invoice.status === 'awaiting_review' && <DecisionForm />}
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
