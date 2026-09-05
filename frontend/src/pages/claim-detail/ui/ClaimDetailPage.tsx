import { Link, useLoaderData, useRevalidator, useRouteError } from 'react-router';
import { ArrowLeft, FileWarning, Loader2 } from 'lucide-react';

import {
  ClaimAttachmentViewer,
  claimCategoryLabel,
  claimStatusBadgeClassName,
  claimStatusLabel,
  claimStatusNotice,
  claimStatusNoticeClassName,
  formatClaimAmount,
  NotFoundError,
} from '@/entities/claim';
import { paths } from '@/shared/config/paths';
import { formatDate } from '@/shared/lib/date';
import { cn } from '@/shared/lib/utils';
import { Badge } from '@/shared/ui/badge';
import { Button } from '@/shared/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/shared/ui/empty';

import type { loader } from '../api/loader';

const pageClassName = 'mx-auto flex max-w-3xl flex-col gap-6 px-5 py-10';

const cardTitleClassName = 'text-xs font-semibold uppercase tracking-wide text-muted-foreground';

export function HydrateFallback() {
  return (
    <div className={pageClassName}>
      <div role="status" className="flex justify-center py-10">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
        <span className="sr-only">Loading claim…</span>
      </div>
    </div>
  );
}

export function ClaimDetailPage() {
  const claim = useLoaderData<typeof loader>();

  return (
    <div className={pageClassName}>
      <BackLink to={paths.claims} label="Back to my claims" />

      <div className="flex items-start justify-between gap-4">
        <div className="flex flex-col gap-2">
          <h1 className="text-2xl leading-none font-semibold tracking-tight">
            {claim.expenseTitle}
          </h1>
          <p className="text-sm text-muted-foreground">
            Submitted{' '}
            {claim.createdAt.toLocaleDateString(undefined, {
              year: 'numeric',
              month: 'short',
              day: 'numeric',
            })}
          </p>
        </div>
        <div className="flex flex-col items-end gap-1.5">
          <Badge variant="secondary" className={claimStatusBadgeClassName(claim.status)}>
            {claimStatusLabel(claim.status)}
          </Badge>
          <span className="text-lg font-semibold pr-2">
            {formatClaimAmount(claim.totalAmount, claim.currency)}
          </span>
        </div>
      </div>

      <StatusCard status={claim.status} />

      <div className="grid gap-6 md:grid-cols-2">
        <div className="flex flex-col gap-6">
          <Card>
            <CardHeader>
              <CardTitle className={cardTitleClassName}>Business context</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col">
              <CardRow label="Purpose" value={claim.businessPurpose} />
              <CardRow label="Category" value={claimCategoryLabel(claim.category)} />
              <CardRow label="Cost center" value={claim.costCenter ?? '—'} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className={cardTitleClassName}>Invoice facts</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col">
              <CardRow label="Vendor" value={claim.vendor} />
              <CardRow label="Invoice number" value={claim.invoiceNumber ?? '—'} />
              <CardRow label="Invoice date" value={formatDate(claim.invoiceDate)} />
              <CardRow label="Currency" value={claim.currency} />
            </CardContent>
          </Card>
        </div>

        <Card className="h-full">
          <CardHeader>
            <CardTitle className={cardTitleClassName}>Document</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-1 flex-col">
            <ClaimAttachmentViewer claimId={claim.id} attachment={claim.attachment} />
          </CardContent>
        </Card>
      </div>
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
    <div className={pageClassName}>
      <BackLink to={paths.claims} label="Back to my claims" />

      {error instanceof NotFoundError ? (
        <Empty>
          <EmptyHeader>
            <EmptyMedia>
              <FileWarning />
            </EmptyMedia>
            <EmptyTitle>Claim not found</EmptyTitle>
          </EmptyHeader>
        </Empty>
      ) : (
        <Empty>
          <EmptyHeader>
            <EmptyTitle>Couldn't load this claim</EmptyTitle>
            <EmptyDescription>Something went wrong. Please try again.</EmptyDescription>
          </EmptyHeader>
          <Button onClick={retry}>Retry</Button>
        </Empty>
      )}
    </div>
  );
}

function StatusCard({ status }: { status: Parameters<typeof claimStatusNotice>[0] }) {
  const isReturnedForInfo = status === 'returned_for_info';

  return (
    <Card>
      <CardHeader>
        <CardTitle className={cardTitleClassName}>Status</CardTitle>
      </CardHeader>
      <CardContent>
        <div
          className={cn(
            'rounded-lg p-3.5 text-sm leading-relaxed',
            claimStatusNoticeClassName(status),
          )}
        >
          {isReturnedForInfo && (
            <span className="mb-1 block font-semibold">Finance asked for more information:</span>
          )}

          <span>{claimStatusNotice(status)}</span>
        </div>
      </CardContent>
    </Card>
  );
}

function CardRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-6 py-2.5 text-sm">
      <dt className="shrink-0 text-muted-foreground">{label}</dt>
      <dd className="min-w-0 text-right font-[350]">{value}</dd>
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
