import type { ActionFunctionArgs } from 'react-router'

import { uploadInvoice, type UploadInvoiceResult } from '@/entities/invoice'

export async function action({ request }: ActionFunctionArgs): Promise<UploadInvoiceResult> {
  const formData = await request.formData()
  const file = formData.get('file')

  if (!(file instanceof File)) {
    return { kind: 'error' }
  }
  return uploadInvoice(file)
}
