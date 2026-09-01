import type { ActionFunctionArgs } from 'react-router';

import { type UploadedInvoice, uploadInvoice } from '@/entities/invoice';
import { redirectOnSessionExpiry } from '@/entities/user';

export async function action({
  request,
}: ActionFunctionArgs): Promise<UploadedInvoice | null | Response> {
  const formData = await request.formData();
  const file = formData.get('file');

  if (!(file instanceof File)) {
    return null;
  }

  try {
    return await uploadInvoice(file);
  } catch (error) {
    return redirectOnSessionExpiry(error) ?? null;
  }
}
