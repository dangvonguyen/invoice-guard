import { apiClient } from '@/shared/api/client';

import type { InvoiceUploadResponse } from '../model/types';

export type UploadInvoiceResult =
  { kind: 'ok'; invoice: InvoiceUploadResponse } | { kind: 'error' };

export async function uploadInvoice(file: File): Promise<UploadInvoiceResult> {
  try {
    const formData = new FormData();
    formData.append('file', file);

    const { data, error } = await apiClient.POST('/invoices', {
      body: formData as unknown as { file: string },
    });

    if (error !== undefined || data?.data === null || data?.data === undefined) {
      return { kind: 'error' };
    }
    return { kind: 'ok', invoice: data.data };
  } catch {
    return { kind: 'error' };
  }
}
