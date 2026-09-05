import { Link } from 'react-router';

import { Badge } from '@/shared/ui/badge';

import { formatClaimAmount } from '../lib/formatClaimAmount';
import { claimCategoryLabel } from '../model/categoryLabel';
import { claimStatusBadgeClassName, claimStatusLabel } from '../model/statusLabel';
import type { ClaimSummary } from '../model/types';

export interface ClaimRowProps {
  claim: ClaimSummary;
}

export function ClaimRow({ claim }: ClaimRowProps) {
  return (
    <Link
      to={`/claims/${claim.id}`}
      className="flex items-center justify-between gap-6 rounded-xl bg-card p-4 text-sm ring-1 ring-foreground/10 transition-colors hover:bg-muted/50"
    >
      <span className="flex flex-1 flex-col gap-1">
        <span className="font-medium">{claim.expenseTitle}</span>
        <span className="flex text-muted-foreground gap-2">
          <span>{claim.vendor}</span>
          <span>·</span>
          <span>{claimCategoryLabel(claim.category)}</span>
          <span>·</span>
          <span>
            {claim.createdAt.toLocaleDateString(undefined, {
              year: 'numeric',
              month: 'short',
              day: 'numeric',
            })}
          </span>
        </span>
        <Badge variant="secondary" className={claimStatusBadgeClassName(claim.status)}>
          {claimStatusLabel(claim.status)}
        </Badge>
      </span>

      <span className="text-[15px] font-semibold self-start">
        {formatClaimAmount(claim.totalAmount, claim.currency)}
      </span>
    </Link>
  );
}
