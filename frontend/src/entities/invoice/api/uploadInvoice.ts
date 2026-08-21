import { apiClient } from '@/shared/api/client';
import { unwrapEnvelope } from '@/shared/api/envelope';

import { toUploadedInvoice } from '../model/mapper';
import type { UploadedInvoice } from '../model/types';

export async function uploadInvoice(file: File): Promise<UploadedInvoice> {
  const formData = new FormData();
  formData.append('file', file);

  const { data: envelope, error } = await apiClient.POST('/invoices', {
    body: formData as unknown as { file: string },
  });

  if (error) {
    throw new Error('Failed to upload invoice');
  }

  const { data: dto } = unwrapEnvelope(envelope);
  return toUploadedInvoice(dto);
}
