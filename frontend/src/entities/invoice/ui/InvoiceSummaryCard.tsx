import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';

import { formatInvoiceDate } from '../lib/formatInvoiceDate';
import type { InvoiceSummary } from '../model/types';

export interface InvoiceSummaryCardProps {
  summary: InvoiceSummary;
}

export function InvoiceSummaryCard({ summary }: InvoiceSummaryCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-2xl">{summary.vendorName}</CardTitle>
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-3 text-xs">
        <div>
          <p className="text-muted-foreground">Amount</p>
          <p className="font-semibold text-base">
            {summary.totalAmount} {summary.currency}
          </p>
        </div>
        <div>
          <p className="text-muted-foreground">Date</p>
          <p className="font-semibold text-base">{formatInvoiceDate(summary.invoiceDate)}</p>
        </div>
      </CardContent>
    </Card>
  );
}
