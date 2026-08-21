import { apiClient } from '@/shared/api/client';
import { unwrapEnvelope } from '@/shared/api/envelope';

import { toInvoice } from '../model/mapper';
import type { Invoice } from '../model/types';

export async function listInvoices(): Promise<Invoice[]> {
  const { data: envelope, error } = await apiClient.GET('/invoices');

  if (error) {
    throw new Error('Failed to fetch invoices');
  }

  const { data: dtos } = unwrapEnvelope(envelope);
  return dtos.map(toInvoice);
}
