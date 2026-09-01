import { Link } from 'react-router';
import { ChevronRight } from 'lucide-react';

import { Badge } from '@/shared/ui/badge';

import type { ReviewQueueItem } from '../model/types';

export interface ReviewQueueRowProps {
  item: ReviewQueueItem;
}

function flagBadgeLabel(flagCount: number): string {
  return flagCount === 0 ? 'No flags' : `${flagCount} flag${flagCount === 1 ? '' : 's'}`;
}

export function ReviewQueueRow({ item }: ReviewQueueRowProps) {
  const title =
    item.summary === null
      ? `Invoice #${item.id.slice(0, 8)}`
      : `${item.summary.vendorName} · ${item.summary.totalAmount} ${item.summary.currency}`;

  return (
    <Link
      to={`/invoices/${item.id}`}
      className="flex items-center justify-between gap-6 rounded-xl bg-card p-4 text-sm ring-1 ring-foreground/10 transition-colors hover:bg-muted/50"
    >
      <span className="flex flex-1 flex-col gap-1">
        <span className="font-medium">{title}</span>
        <span className="text-muted-foreground">
          Submitted{' '}
          {item.submittedAt.toLocaleDateString(undefined, {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
          })}
        </span>
      </span>
      <span className="flex items-center gap-3">
        <Badge variant={item.flagCount === 0 ? 'outline' : 'destructive'}>
          {flagBadgeLabel(item.flagCount)}
        </Badge>
        <ChevronRight className="size-4 text-muted-foreground" aria-hidden="true" />
      </span>
    </Link>
  );
}
