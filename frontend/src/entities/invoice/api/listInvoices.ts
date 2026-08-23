import { apiClient } from '@/shared/api/client';
import { unwrapEnvelope } from '@/shared/api/envelope';
import { translateApiError } from '@/shared/api/errors';

import { toInvoice } from '../model/mapper';
import type { Invoice } from '../model/types';

export async function listInvoices(): Promise<Invoice[]> {
  const { data: envelope, error, response } = await apiClient.GET('/invoices');

  if (error) {
    throw translateApiError(response, error, 'Failed to fetch invoices');
  }

  const { data: dtos } = unwrapEnvelope(envelope);
  return dtos.map(toInvoice);
}
