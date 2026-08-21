import { apiClient } from '@/shared/api/client';
import { unwrapEnvelope } from '@/shared/api/envelope';

import { toInvoiceDetail } from '../model/mapper';
import type { InvoiceDetail } from '../model/types';

export class NotFoundError extends Error {
  constructor() {
    super('Invoice not found');
    this.name = 'NotFoundError';
  }
}

export async function getInvoice(invoiceId: string): Promise<InvoiceDetail> {
  const {
    data: envelope,
    error,
    response,
  } = await apiClient.GET('/invoices/{invoice_id}', {
    params: { path: { invoice_id: invoiceId } },
  });

  if (error) {
    if (response.status === 404) throw new NotFoundError();
    throw new Error('Failed to fetch invoice');
  }

  const { data: dto } = unwrapEnvelope(envelope);

  if ('employee' in dto) {
    throw new Error('Unsupported invoice view');
  }

  return toInvoiceDetail(dto);
}
