import { Link } from 'react-router'
import { ChevronRight } from 'lucide-react'

import { Badge } from '@/shared/ui/badge'

import { invoiceStatusBadgeVariant, invoiceStatusLabel } from '../model/statusLabel'
import type { InvoiceListItem } from '../model/types'

export interface InvoiceRowProps {
  invoice: InvoiceListItem
  index: number
}

export function InvoiceRow({ invoice, index }: InvoiceRowProps) {
  const submittedAt = new Date(invoice.created_at)

  return (
    <Link
      to={`/invoices/${invoice.id}`}
      className="flex items-center justify-between gap-6 rounded-xl bg-card p-4 text-sm ring-1 ring-foreground/10 transition-colors hover:bg-muted/50"
    >
      <span className="w-2">{index}.</span>
      <span className="text-muted-foreground flex flex-1">
        Submitted{' '}
        {submittedAt.toLocaleDateString(undefined, {
          year: 'numeric',
          month: 'short',
          day: 'numeric',
        })}
      </span>
      <span className="flex items-center gap-3">
        <Badge variant={invoiceStatusBadgeVariant(invoice.status)}>
          {invoiceStatusLabel(invoice.status)}
        </Badge>
        <ChevronRight className="size-4 text-muted-foreground" aria-hidden="true" />
      </span>
    </Link>
  )
}
