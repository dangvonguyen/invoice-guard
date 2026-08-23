import { apiClient } from '@/shared/api/client';
import { unwrapEnvelope } from '@/shared/api/envelope';
import { translateApiError } from '@/shared/api/errors';

import { toInvoiceDetail, toReviewerInvoiceDetail } from '../model/mapper';
import type { InvoiceDetailView } from '../model/types';

export class NotFoundError extends Error {
  constructor() {
    super('Invoice not found');
    this.name = 'NotFoundError';
  }
}

export async function getInvoice(invoiceId: string): Promise<InvoiceDetailView> {
  const {
    data: envelope,
    error,
    response,
  } = await apiClient.GET('/invoices/{invoice_id}', {
    params: { path: { invoice_id: invoiceId } },
  });

  if (error) {
    throw translateApiError(response, error, 'Failed to fetch invoice', {
      404: () => new NotFoundError(),
    });
  }

  const { data: dto } = unwrapEnvelope(envelope);

  if ('employee' in dto) {
    return toReviewerInvoiceDetail(dto);
  }

  return toInvoiceDetail(dto);
}
