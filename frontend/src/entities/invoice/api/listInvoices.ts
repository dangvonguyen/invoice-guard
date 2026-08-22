import { apiClient } from '@/shared/api/client';
import { unwrapEnvelope } from '@/shared/api/envelope';
import { UnauthenticatedError } from '@/shared/api/errors';

import { toInvoice } from '../model/mapper';
import type { Invoice } from '../model/types';

export async function listInvoices(): Promise<Invoice[]> {
  const { data: envelope, error, response } = await apiClient.GET('/invoices');

  if (error) {
    if (response.status === 401) throw new UnauthenticatedError();
    throw new Error('Failed to fetch invoices');
  }

  const { data: dtos } = unwrapEnvelope(envelope);
  return dtos.map(toInvoice);
}
