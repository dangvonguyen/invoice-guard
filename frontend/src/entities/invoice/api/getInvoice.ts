import { apiClient } from '@/shared/api/client'

import type { InvoiceDetailResponse } from '../model/types'

export type GetInvoiceResult =
  { kind: 'ok'; invoice: InvoiceDetailResponse } | { kind: 'not_found' } | { kind: 'error' }

export async function getInvoice(invoiceId: string): Promise<GetInvoiceResult> {
  try {
    const { data, error, response } = await apiClient.GET('/invoices/{invoice_id}', {
      params: { path: { invoice_id: invoiceId } },
    })

    if (error !== undefined || data?.data === null || data?.data === undefined) {
      if (response.status === 404) {
        return { kind: 'not_found' }
      }
      return { kind: 'error' }
    }

    if ('employee' in data.data) {
      return { kind: 'error' }
    }

    return { kind: 'ok', invoice: data.data }
  } catch {
    return { kind: 'error' }
  }
}
