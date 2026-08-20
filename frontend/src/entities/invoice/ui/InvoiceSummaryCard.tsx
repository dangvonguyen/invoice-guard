import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card'

import { formatInvoiceDate } from '../lib/formatInvoiceDate'
import type { InvoiceSummary } from '../model/types'

export interface InvoiceSummaryCardProps {
  summary: InvoiceSummary
}

export function InvoiceSummaryCard({ summary }: InvoiceSummaryCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-2xl">{summary.vendor_name}</CardTitle>
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-3 text-xs">
        <div>
          <p className="text-muted-foreground">Amount</p>
          <p className="font-semibold text-base">
            {summary.total_amount} {summary.currency}
          </p>
        </div>
        <div>
          <p className="text-muted-foreground">Date</p>
          <p className="font-semibold text-base">{formatInvoiceDate(summary.invoice_date)}</p>
        </div>
      </CardContent>
    </Card>
  )
}
