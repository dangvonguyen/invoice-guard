import type { ActionFunctionArgs } from 'react-router';

import { type UploadedInvoice, uploadInvoice } from '@/entities/invoice';

export async function action({ request }: ActionFunctionArgs): Promise<UploadedInvoice | null> {
  const formData = await request.formData();
  const file = formData.get('file');

  if (!(file instanceof File)) {
    return null;
  }

  try {
    return await uploadInvoice(file);
  } catch {
    return null;
  }
}
